"""Concrete manufacturer protocol adapters. No generic/pretend device driver.

Device identity and source mode come from enrollment, never from a device's claim.
Switch has aggregate metering, not per-gang metering; GPIO intent is not feedback.
Presence light is an uncalibrated ADC count, never lux or continuous occupancy.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import re
import struct
from contract import CAPABILITIES, PRODUCTS, event_identity, validate_descriptor, validate_event
from wire import validate_telemetry, validate_ack

IDENTITY = re.compile(r'^[A-Za-z0-9_-]{1,47}$')
BOOT = re.compile(r'^[0-9a-f]{32}$')
UINT = re.compile(r'^(0|[1-9][0-9]{0,19})$')


def iso(now: float) -> str:
    return datetime.fromtimestamp(now, timezone.utc).isoformat().replace('+00:00', 'Z')


def uint(value, maximum=2**64 - 1):
    if not isinstance(value, str) or not UINT.fullmatch(value) or int(value) > maximum:
        raise ValueError('canonical bounded unsigned decimal required')
    return int(value)


def number(value, low=-1e9, high=1e9):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('finite measurement out of range')
    return value


def boolean(value):
    if type(value) is not bool:
        raise ValueError('boolean required')
    return value


@dataclass(frozen=True)
class Enrollment:
    device_id: str
    product_family: str
    protocol: str
    source_mode: str = 'REAL'
    ble_address: str | None = None
    ble_identity: int | None = None
    profile_id: str | None = None
    auth_key_file: str | None = None

    def __post_init__(self):
        if not isinstance(self.device_id, str) or not IDENTITY.fullmatch(self.device_id):
            raise ValueError('invalid enrollment identity')
        allowed = {'PLUG': {'plug-wire-v2'}, 'SWITCH': {'switch-mqtt-v1'}, 'PRESENCE': {'presence-ble-v2', 'presence-gatt-v1'}}
        if self.product_family not in allowed or self.protocol not in allowed[self.product_family]:
            raise ValueError('unsupported family/protocol')
        if self.source_mode not in {'REAL', 'SIMULATED', 'REPLAYED'}:
            raise ValueError('invalid enrollment source')
        if self.product_family == 'PRESENCE':
            if not isinstance(self.ble_address, str) or not re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', self.ble_address):
                raise ValueError('explicit fixed BLE enrollment address required')
            if self.protocol in {'presence-ble-v2', 'presence-gatt-v1'} and (type(self.ble_identity) is not int or not 0 < self.ble_identity < 2**32):
                raise ValueError('explicit BLE manufacturer identity required')


def reading(capability, channel, value, quality='valid', **details):
    out = {'capability': capability, 'channel_id': channel, 'value': value,
           'unit': CAPABILITIES[capability]['unit'], 'quality': quality}
    if details:
        out['details'] = details
    return out


def event(enrollment, boot, sequence, now, monotonic, readings, raw, quality='partial', observed=None, time_quality='gateway_received'):
    return validate_event({
        'schema_version': 1, 'event_id': event_identity(enrollment.device_id, boot, str(sequence)),
        'device_id': enrollment.device_id, 'product_family': enrollment.product_family,
        'boot_id': boot, 'sequence': str(sequence), 'observed_at': observed,
        'received_at': iso(now), 'monotonic_ms': monotonic, 'source_mode': enrollment.source_mode,
        'source_protocol': enrollment.protocol, 'time_quality': time_quality, 'quality': quality,
        'readings': readings, 'raw': raw,
    })


def descriptor(enrollment: Enrollment):
    from copy import deepcopy
    product = PRODUCTS[enrollment.product_family]
    return validate_descriptor({'schema_version':1, 'device_id':enrollment.device_id,
        'product_family':enrollment.product_family, 'model':product['model'],
        'protocol':enrollment.protocol, 'channels':deepcopy(product['channels'])})


class PlugAdapter:
    @staticmethod
    def telemetry(enrollment, raw, now):
        validate_telemetry(raw, enrollment.device_id)
        readings = []
        for cap, key in [('power.active', 'active_w'), ('voltage.rms', 'voltage_v'), ('current.rms', 'current_a')]:
            readings.append(reading(cap, 'meter.aggregate', raw.get(key), 'valid' if raw['valid'] else 'invalid', calibrated=raw['calibrated']))
        for cap, key in [('energy.import', 'known_forward_wh_since_boot'), ('energy.export', 'known_reverse_wh_since_boot')]:
            readings.append(reading(cap, 'meter.aggregate', raw[key] if raw['calibrated'] else None,
                'partial' if raw['calibrated'] else 'unavailable', scope='known_intervals_since_boot', uncertain_intervals=raw['energy_uncertain_intervals'], billing_certified=False))
        readings.append(reading('relay.commanded', 'relay.1', raw['desired_on']))
        readings.append(reading('relay.feedback', 'relay.1', raw['output_present'] if raw['feedback_valid'] else None,
            'valid' if raw['feedback_valid'] else 'unknown', method='optical_output_presence', sensing=raw['output_sensing'], voltage_absence_proven=False, independent_contact_feedback=False))
        local = raw.get('last_local_input', {})
        if not isinstance(local, dict):
            raise ValueError('invalid local control metadata')
        mode = raw.get('control_mode')
        if raw['fault_latched']:
            mode = 'protected'
        readings.append(reading('control.mode', 'relay.1', mode, 'valid' if mode is not None else 'unknown'))
        hold = raw.get('manual_hold_until_uptime_ms')
        if hold is not None:
            hold = uint(hold, 2**53 - 1)
        if hold is not None:
            number(hold, 0, 2**53 - 1)
        readings.append(reading('control.manual_hold_until', 'relay.1', hold, 'valid' if hold is not None else 'unknown'))
        if local:
            local_seq = uint(local.get('event_seq'))
            local_uptime = uint(local.get('uptime_ms'), raw['monotonic_ms'])
            readings.append(reading('button.local', 'button.1', boolean(local.get('pressed')), event_sequence=str(local_seq), event_monotonic_ms=local_uptime, semantics='last_event_not_continuous_pressed', result=local.get('result')))
        readings.append(reading('device.health', 'device', 'fault' if raw['fault_latched'] else 'maintenance' if raw.get('maintenance') else 'ok', fault_latched=raw['fault_latched'], maintenance=raw.get('maintenance', False), actuation_enabled=raw.get('actuation_enabled', False)))
        observed = iso(raw['unix_s']) if raw['time_quality'] == 'authenticated' else None
        return event(enrollment, raw['boot_epoch'], raw['sample_seq'], now, raw['monotonic_ms'], readings, raw,
            observed=observed, time_quality='authenticated' if observed else 'unknown')


class SwitchAdapter:
    @staticmethod
    def telemetry(enrollment, raw, now):
        if not isinstance(raw, dict) or raw.get('device_id') != enrollment.device_id or type(raw.get('schema_version')) is not int or raw['schema_version'] != 1:
            raise ValueError('Switch wire schema 1 and matching identity required')
        if not isinstance(raw.get('boot_id'), str) or not BOOT.fullmatch(raw['boot_id']):
            raise ValueError('Switch boot identity required')
        if raw.get('source_mode') != enrollment.source_mode:
            raise ValueError('Switch source/enrollment mismatch')
        sequence = uint(raw.get('sample_seq'))
        if sequence == 0:
            raise ValueError('Switch sample sequence must be positive')
        uptime = uint(raw.get('uptime_ms'), 2**53 - 1)
        uint(raw.get('last_seq'))
        fault = boolean(raw.get('fault_latched'))
        maintenance = boolean(raw.get('maintenance'))
        boolean(raw.get('actuation_enabled'))
        protected = raw.get('protected_channel_mask')
        if type(protected) is not int or not 0 <= protected <= 7:
            raise ValueError('invalid protected channel mask')
        channels = raw.get('channels')
        if not isinstance(channels, list) or len(channels) != 3:
            raise ValueError('exactly three Switch channels required')
        seen = set(); readings = []
        for ch in channels:
            index = ch.get('channel') if isinstance(ch, dict) else None
            if type(index) is not int or index not in {1, 2, 3} or index in seen or ch.get('channel_id') != f'lighting-{index}':
                raise ValueError('invalid Switch channel identity')
            seen.add(index); cid = f'relay.{index}'
            desired = boolean(ch.get('commanded_on'))
            if ch.get('physically_verified_on', False) is not None or ch.get('feedback_quality') != 'unavailable_no_independent_sensor':
                raise ValueError('Switch cannot assert independent physical verification')
            mode = ch.get('control_mode')
            if mode not in {'auto', 'manual', 'maintenance', 'protected'}:
                raise ValueError('invalid control mode')
            hold = uint(ch.get('manual_hold_until_uptime_ms'), 2**53 - 1)
            readings += [reading('relay.commanded', cid, desired),
                reading('relay.feedback', cid, None, 'unavailable', reason='no_independent_sensor'),
                reading('control.mode', cid, mode), reading('control.manual_hold_until', cid, hold)]
        meter = raw.get('aggregate_meter')
        if not isinstance(meter, dict) or meter.get('scope') != 'three_lighting_outputs_total':
            raise ValueError('aggregate metering scope required')
        quality = meter.get('quality')
        if quality not in {'unavailable', 'uncalibrated', 'calibrated_readback'}:
            raise ValueError('invalid Switch meter quality')
        fresh = quality != 'unavailable'
        if fresh and not 0 <= uptime - uint(meter.get('observed_uptime_ms'), 2**53 - 1) <= 5000:
            raise ValueError('meter freshness inconsistent')
        for cap, key, low in [('power.active', 'active_power_w', -1e6), ('voltage.rms', 'voltage_v', 0), ('current.rms', 'current_a', 0)]:
            value = meter.get(key)
            if quality == 'calibrated_readback':
                number(value, low, 1e6)
            elif value is not None:
                raise ValueError('uncalibrated/unavailable meter must not publish engineering values')
            readings.append(reading(cap, 'meter.aggregate', value, 'valid' if quality == 'calibrated_readback' else 'unavailable', meter_quality=quality, scope=meter['scope']))
        if meter.get('energy_quality') != 'partial_lower_bound':
            raise ValueError('Switch energy remains an explicit partial lower bound')
        if quality == 'calibrated_readback' and (not isinstance(meter.get('calibration_id'), str) or not meter['calibration_id']):
            raise ValueError('calibrated Switch measurement requires calibration identity')
        energy = meter.get('known_energy_wh')
        gaps = meter.get('unknown_intervals')
        if type(gaps) is not int or not 0 <= gaps <= 2**32 - 1:
            raise ValueError('invalid energy uncertainty counter')
        storage = boolean(meter.get('persistent_storage_ok'))
        if energy is not None:
            if not storage or not isinstance(energy, str) or not re.fullmatch(r'[0-9]{1,17}\.[0-9]{3}', energy):
                raise ValueError('invalid Switch partial energy')
            energy = number(float(energy), 0, 2**53 - 1)
        readings += [reading('energy.import', 'meter.aggregate', energy, 'partial' if energy is not None else 'unavailable', scope='device_total', uncertain_intervals=gaps, billing_certified=False, lower_bound=True),
            reading('energy.export', 'meter.aggregate', None, 'unavailable', reason='no_accumulated_export_measurement')]
        local = raw.get('last_local_input')
        if not isinstance(local, dict):
            raise ValueError('local button metadata required')
        local_seq = uint(local.get('event_seq'))
        local_time = uint(local.get('uptime_ms'), uptime)
        local_channel = local.get('channel')
        if type(local_channel) is not int or local_channel not in ({1, 2, 3} if local_seq else {0}):
            raise ValueError('invalid local button channel')
        pressed = boolean(local.get('pressed'))
        if pressed != (local_seq > 0):
            raise ValueError('invalid local button event state')
        for i in range(1, 4):
            readings.append(reading('button.local', f'button.{i}', pressed if local_channel == i else False,
                event_sequence=str(local_seq), event_monotonic_ms=local_time, event_channel=local_channel,
                semantics='last_event_not_continuous_pressed', result=local.get('result')))
        readings.append(reading('device.health', 'device', 'fault' if fault else 'maintenance' if maintenance else 'ok',
            fault_latched=fault, maintenance=maintenance, actuation_enabled=raw['actuation_enabled'], protected_channel_mask=protected))
        return event(enrollment, raw['boot_id'], sequence, now, uptime, readings, raw)


class PresenceAdapter:
    @staticmethod
    def parse_v2(payload: bytes):
        # Bleak manufacturer_data excludes the two-byte company identifier.
        if not isinstance(payload, bytes) or len(payload) != 24:
            raise ValueError('Presence v2 requires exactly 24 manufacturer bytes')
        version, flags, radar, error, identity, boot, sequence, light, buffer_mv, uptime_s = struct.unpack('<BBBBIIIHHI', payload)
        if version != 2 or flags & 1 or radar > 2 or identity == 0 or boot == 0 or sequence == 0:
            raise ValueError('invalid Presence v2 version, identity, boot or radar enum')
        return dict(version=version, flags=flags, radar=radar, radar_error=error, identity=identity,
            boot=boot, sample_seq=sequence, light_raw=light, buffer_mv=buffer_mv, monotonic_s=uptime_s)

    @staticmethod
    def telemetry(enrollment, payload, now):
        if enrollment.protocol != 'presence-ble-v2':
            raise ValueError('Legacy Presence v1 lacks boot identity and valid flags; parse-only, not authoritative ingestion')
        raw = PresenceAdapter.parse_v2(payload)
        if raw['identity'] != enrollment.ble_identity:
            raise ValueError('BLE manufacturer identity does not match enrollment')
        flags = raw['flags']; warm, low, missing = bool(flags & 2), bool(flags & 4), bool(flags & 8)
        health = 'warming' if warm else 'low_buffer' if low else 'radar_unavailable' if missing else 'radar_error' if raw['radar_error'] else 'ok'
        pir_good = not warm and not low
        radar_good = pir_good and not missing and raw['radar_error'] == 0 and raw['radar'] in {1, 2}
        light_good, buffer_good = bool(flags & 64), bool(flags & 128)
        readings = [reading('presence.radar', 'sensor.radar', raw['radar'] == 2 if radar_good else None, 'partial' if radar_good else 'unavailable', continuous_occupancy=False, sample_only=True, radar_error=raw['radar_error'], driver_ready=not missing, authenticity='unauthenticated_ble'),
            reading('illuminance.raw', 'sensor.light', raw['light_raw'] if light_good else None, 'uncalibrated' if light_good else 'unknown', calibrated=False, not_lux=True),
            reading('buffer.voltage', 'sensor.buffer', raw['buffer_mv'] if buffer_good else None, 'valid' if buffer_good else 'unknown'),
            reading('button.local', 'button.1', bool(flags & 32), semantics='sample_event_flag'),
            reading('device.health', 'device', health, warming=warm, low_buffer=low, radar_driver_ready=not missing, radar_error=raw['radar_error'], authenticity='unauthenticated_ble')]
        evidence = {**raw, 'manufacturer_data_hex': payload.hex(), 'manufacturer_company_id': 65535}
        return event(enrollment, f'adv-{raw["boot"]:08x}', raw['sample_seq'], now, raw['monotonic_s'] * 1000, readings, evidence)

