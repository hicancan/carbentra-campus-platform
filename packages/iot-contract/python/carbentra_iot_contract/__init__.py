"""CARBENTRA IoT application contract v1, independent of manufacturer wire versions.

JSON Schemas are the syntax authority; these checks enforce cross-field identity,
finite values, uint64 boundaries, and measurement truth the schema cannot express.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / 'schemas').is_dir():
    ROOT = Path(__file__).resolve().parent / 'data'
SCHEMAS = ROOT / 'schemas'
CAPABILITIES = json.loads((ROOT / 'capabilities.json').read_text(encoding="utf-8"))
PRODUCTS = json.loads((ROOT / 'products.json').read_text(encoding="utf-8"))
PRESENCE_GATT = json.loads((ROOT / 'protocols/presence-gatt-v1.json').read_text(encoding="utf-8"))
_VALIDATORS = {
    kind: Draft202012Validator(json.loads((SCHEMAS / f'{kind}.schema.json').read_text(encoding="utf-8")), format_checker=FormatChecker())
    for kind in ('event', 'descriptor', 'command', 'switch-ack')
}


def event_identity(device_id: str, boot_id: str, sequence: str) -> str:
    """Stable across retries, gateway restarts and serialization order."""
    return sha256(f'carbentra-iot-v1\n{device_id}\n{boot_id}\n{sequence}'.encode()).hexdigest()


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timezone required')
    return parsed.astimezone(timezone.utc)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('nonfinite number')
    if isinstance(value, dict):
        for item in value.values():
            _finite(item)
    elif isinstance(value, list):
        for item in value:
            _finite(item)


def validate(kind: str, value: dict) -> dict:
    _finite(value)
    errors = sorted(_VALIDATORS[kind].iter_errors(value), key=lambda e: str(list(e.path)))
    if errors:
        error = errors[0]
        raise ValueError(f'{kind} schema violation at {".".join(map(str, error.path))}: {error.message}')
    if kind in {'event', 'command'} and int(value['sequence']) >= 2**64:
        raise ValueError('sequence exceeds uint64')
    if kind == 'event':
        expected = event_identity(value['device_id'], value['boot_id'], value['sequence'])
        if value['event_id'] != expected:
            raise ValueError('event identity mismatch')
        if value['observed_at'] is None and value['time_quality'] in {'authenticated', 'device_clock'}:
            raise ValueError('device time quality requires observed_at')
        if value['time_quality'] in {'unknown', 'gateway_received'} and value['observed_at'] is not None:
            raise ValueError('gateway arrival must not invent device observation time')
        declared = {channel['channel_id']:{cap['capability']:cap for cap in channel['capabilities']} for channel in PRODUCTS[value['product_family']]['channels']}
        seen = set()
        for reading in value['readings']:
            pair = reading['channel_id'], reading['capability']
            supported = declared.get(pair[0], {}).get(pair[1])
            if supported is None:
                raise ValueError('capability/channel not supported by this product family')
            if not supported['available'] and (reading['quality'] != 'unavailable' or reading['value'] is not None):
                raise ValueError('unsupported physical capability must remain unavailable')
            if pair in seen:
                raise ValueError('duplicate channel capability')
            seen.add(pair)
            if reading['quality'] in {'invalid', 'unknown', 'unavailable'} and reading['value'] is not None:
                raise ValueError('unusable reading must be null')
            if reading['quality'] == 'valid' and reading['value'] is None:
                raise ValueError('valid reading cannot be null')
            if reading['capability'] in {'energy.import', 'energy.export', 'illuminance.raw', 'buffer.voltage', 'voltage.rms', 'current.rms'} and reading['value'] is not None and reading['value'] < 0:
                raise ValueError('negative unsigned measurement')
            if reading['capability'] == 'relay.feedback' and (reading.get('details',{}).get('voltage_absence_proven') is True or reading.get('details',{}).get('independent_contact_feedback') is True):
                raise ValueError('current product feedback cannot prove contact isolation or safe voltage absence')
            if reading['capability'] in {'illuminance.raw','buffer.voltage'} and reading['value'] is not None and reading['value'] > 65535:
                raise ValueError('16-bit sensor value out of range')
            if value['source_protocol'] == 'presence-ble-v2' and reading['capability'] == 'presence.radar':
                if reading['quality'] == 'valid' or reading.get('details',{}).get('continuous_occupancy') is not False or reading.get('details',{}).get('authenticity') != 'unauthenticated_ble':
                    raise ValueError('unauthenticated advertisement cannot assert trustworthy continuous occupancy')
            if reading['capability'] == 'control.mode' and reading['value'] not in {None, 'auto', 'manual', 'maintenance', 'protected'}:
                raise ValueError('unsupported control mode')
        if value['source_protocol'] == 'virtual-v1' and value['source_mode'] != 'SIMULATED':
            raise ValueError('virtual protocol requires explicit simulated source')
        if value['source_protocol'] == 'plug-wire-v2':
            raw = value['raw']
            if value['product_family'] != 'PLUG' or raw.get('device_id') != value['device_id'] or raw.get('boot_epoch') != value['boot_id'] or raw.get('sample_seq') != value['sequence']:
                raise ValueError('plug raw identity mismatch')
        if value['source_protocol'].startswith('presence-ble') and value['product_family'] != 'PRESENCE':
            raise ValueError('BLE family mismatch')
        if value['source_protocol'] == 'switch-mqtt-v1':
            raw = value['raw']
            if value['product_family'] != 'SWITCH' or raw.get('device_id') != value['device_id'] or raw.get('boot_id') != value['boot_id'] or raw.get('sample_seq') != value['sequence'] or raw.get('source_mode') != value['source_mode']:
                raise ValueError('Switch raw identity/source mismatch')
        if value['source_protocol'] in {'presence-ble-v2', 'presence-gatt-v1'}:
            raw = value['raw']
            expected_boot = (('adv-' if value['source_protocol']=='presence-ble-v2' else '') + f"{raw.get('boot',0):08x}") if type(raw.get('boot')) is int else None
            if value['product_family'] != 'PRESENCE' or expected_boot != value['boot_id'] or str(raw.get('sample_seq')) != value['sequence']:
                raise ValueError('Presence raw identity mismatch')
        if value['source_protocol'] == 'presence-gatt-v1':
            raw=value['raw']
            try:
                response=bytes.fromhex(raw['response_hex'])
                frame=bytes.fromhex(raw['manufacturer_data_hex'])
            except (KeyError,TypeError,ValueError) as error:
                raise ValueError('authenticated event requires original proof bytes') from error
            if len(response)!=86 or response[0]!=1 or response[1:25]!=frame or raw.get('authentication')!='hmac-sha256-nonce-v1' or raw.get('proof_sha256')!=sha256(response).hexdigest():
                raise ValueError('authenticated event proof evidence is inconsistent')
            if int.from_bytes(response[9:13],'little')!=raw.get('boot') or int.from_bytes(response[13:17],'little')!=raw.get('sample_seq') or int.from_bytes(response[5:9],'little')!=raw.get('identity') or response[53]!=raw.get('evidence_flags'):
                raise ValueError('authenticated proof identity/flags differ from envelope')
            signed_radar_age=int.from_bytes(response[45:49],'little')
            if signed_radar_age!=raw.get('radar_age_ms'):
                raise ValueError('authenticated radar age differs from proof')
            for reading in value['readings']:
                if reading.get('details',{}).get('authenticity')!='authenticated_gatt_hmac_sha256':
                    raise ValueError('authenticated channel provenance is missing')
                if reading['capability']=='presence.radar' and reading['quality']=='valid':
                    details=reading.get('details',{})
                    age=details.get('measurement_age_ms')
                    if details.get('continuous_occupancy') is not True or type(age) not in (int,float) or not 0<=age<=5000 or response[53]&5!=5 or age<signed_radar_age or response[3] not in (1,2) or reading['value']!=(response[3]==2) or response[2]&14 or response[4]!=0:
                        raise ValueError('valid radar requires fresh continuous authenticated evidence')
    elif kind == 'descriptor':
        declared = {channel['channel_id']:{cap['capability']:cap for cap in channel['capabilities']} for channel in PRODUCTS[value['product_family']]['channels']}
        seen = set()
        for channel in value['channels']:
            if channel['channel_id'] in seen:
                raise ValueError('duplicate channel')
            seen.add(channel['channel_id'])
            caps = set()
            for cap in channel['capabilities']:
                supported = declared.get(channel['channel_id'],{}).get(cap['capability'])
                if supported is None or (cap['available'] and not supported['available']):
                    raise ValueError('descriptor overclaims product capability')
                if cap['capability'] in caps:
                    raise ValueError('duplicate capability')
                caps.add(cap['capability'])
                if cap['unit'] != CAPABILITIES[cap['capability']]['unit']:
                    raise ValueError('capability unit mismatch')
                if cap['access'] != 'read' and cap['capability'] != 'relay.commanded':
                    raise ValueError('only declared relay state is writable')
    elif kind == 'command':
        issued, expires = timestamp(value['issued_at']), timestamp(value['expires_at'])
        lease = timestamp(value['authority']['lease_expires_at'])
        if not 0 < (expires - issued).total_seconds() <= 60:
            raise ValueError('command window must be at most 60 seconds')
        if expires > lease:
            raise ValueError('command expiry exceeds authority lease')
        if lease <= issued:
            raise ValueError('authority lease expired before command')
        if value['sequence'] == '0':
            raise ValueError('command sequence must be positive')
        if 'manual_hold_seconds' in value and value['authority']['kind'] != 'manual':
            raise ValueError('manual hold requires explicit manual command authority')
        if value['authority']['kind'] == 'local_rule' and not value['authority'].get('rule_id'):
            raise ValueError('local rule identity required')
        if value['channel_id'] not in ({'relay.1'} if value['product_family'] == 'PLUG' else {'relay.1', 'relay.2', 'relay.3'}):
            raise ValueError('unknown relay channel')
    elif kind == 'switch-ack':
        if int(value['seq']) >= 2**64 or int(value['uptime_ms']) > 2**53 - 1:
            raise ValueError('ACK sequence or uptime out of bounds')
    return value


def validate_switch_ack(value: dict) -> dict:
    return validate('switch-ack', value)


def validate_event(value: dict) -> dict:
    return validate('event', value)


def validate_descriptor(value: dict) -> dict:
    return validate('descriptor', value)


def validate_command(value: dict) -> dict:
    return validate('command', value)
