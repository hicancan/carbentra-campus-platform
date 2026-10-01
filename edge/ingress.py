"""Exact-topic MQTT admission and explicit enrolled BLE identity admission."""
from __future__ import annotations
import re
from dataclasses import replace
import time
from adapters import Enrollment, PlugAdapter, SwitchAdapter, PresenceAdapter, boolean, uint
from service import strict_json
from store import EdgeStore
from contract import validate_event
from adapters import iso
from wire import validate_ack


class Ingress:
    def __init__(self, store: EdgeStore, enrollments):
        self.store = store
        self.enrolled = {e.device_id: e for e in enrollments}
        if len(self.enrolled) != len(enrollments):
            raise ValueError('duplicate enrollment')
        addresses = [e.ble_address.lower() for e in enrollments if e.ble_address]
        if len(addresses) != len(set(addresses)):
            raise ValueError('duplicate BLE enrollment address')

    def topics(self):
        for e in self.enrolled.values():
            if e.source_mode == 'SIMULATED' and e.product_family == 'PRESENCE':
                yield f'carbentra/virtual/{e.device_id}/event'
            if e.product_family == 'PLUG':
                for kind in ('hello', 'telemetry', 'ack'):
                    yield f'carbentra/v1/{e.device_id}/{kind}'
            elif e.product_family == 'SWITCH':
                for kind in ('state', 'ack', 'availability'):
                    yield f'carbentra/switch/{e.device_id}/{kind}'

    def mqtt(self, topic, payload, retained=False, now=None):
        now = time.time() if now is None else now
        if retained:
            # A retained state/ACK can be arbitrarily old; never refresh control evidence.
            return None
        parts = topic.split('/')
        if len(parts) != 4 or parts[0] != 'carbentra':
            raise ValueError('invalid exact topic')
        namespace, device, kind = parts[1:]
        e = self.enrolled.get(device)
        if e is None:
            raise ValueError('device is not enrolled')
        if namespace == 'virtual' and kind == 'event' and e.source_mode == 'SIMULATED' and e.product_family == 'PRESENCE':
            raw = strict_json(payload, maximum=16384)
            validate_event(raw)
            if raw['device_id'] != device or raw['product_family'] != 'PRESENCE' or raw['source_mode'] != 'SIMULATED' or raw['source_protocol'] != 'virtual-v1':
                raise ValueError('virtual event enrollment/source mismatch')
            raw['received_at'] = iso(now)
            self.store.accept_event(raw)
            return None
        if namespace == 'v1' and e.product_family == 'PLUG':
            raw = strict_json(payload)
            if not isinstance(raw, dict):
                raise ValueError('object required')
            if kind == 'hello':
                nonce = raw.get('clock_nonce')
                if not isinstance(nonce, str) or not re.fullmatch('[0-9a-f]{32}', nonce):
                    raise ValueError('bad clock nonce')
                return f'carbentra/v1/{device}/time', {'clock_nonce': nonce, 'unix_s': int(now)}
            if kind == 'telemetry':
                event = PlugAdapter.telemetry(e, raw, now)
                self.store.accept_event(event)
                return f'carbentra/v1/{device}/receipt', {'boot_epoch': raw['boot_epoch'], 'sample_seq': raw['sample_seq']}
            if kind == 'ack':
                validate_ack(raw, device)
                self.store.accept_ack('ack', device, raw, now)
                return None
        elif namespace == 'switch' and e.product_family == 'SWITCH':
            if kind == 'availability':
                if payload not in {b'online', b'offline', 'online', 'offline'}:
                    raise ValueError('invalid availability')
                self.store.health('mqtt:' + device, {'availability': payload.decode() if isinstance(payload, bytes) else payload}, now)
                return None
            raw = strict_json(payload)
            if kind == 'state':
                self.store.accept_event(SwitchAdapter.telemetry(e, raw, now))
                return None
            if kind == 'ack':
                validate_switch_ack(raw, device)
                self.store.accept_ack('switch_ack', device, raw, now)
                return None
        raise ValueError('unsupported device/topic direction')

    def ble(self, address, manufacturer_data, now=None):
        now = time.time() if now is None else now
        e = next((e for e in self.enrolled.values() if e.ble_address and e.ble_address.lower() == address.lower()), None)
        if e is None:
            raise ValueError('BLE address is not enrolled')
        if e.source_mode != 'REAL':
            raise ValueError('actual radio input cannot claim simulated/replayed source')
        payload = manufacturer_data.get(65535)
        if not isinstance(payload, bytes):
            raise ValueError('Presence manufacturer payload missing')
        value = PresenceAdapter.telemetry(replace(e, protocol='presence-ble-v2') if e.protocol == 'presence-gatt-v1' else e, payload, now)
        if e.protocol == 'presence-gatt-v1':
            # Discovery bytes have no authority over the signed snapshot namespace
            # or backend observation timeline, even when a MAC address is enrolled.
            self.store.health('ble-diagnostic:' + e.device_id, {'authenticated':False,'diagnostic_only':True,'boot_id':value['boot_id'],'sequence':value['sequence'],'raw':value['raw']}, now)
            return {'durable':True,'diagnostic_only':True,'authenticated':False}
        return self.store.accept_event(value)


def validate_switch_ack(raw, device):
    from contract import validate_switch_ack as validate
    validate(raw)
    if raw['device_id'] != device:
        raise ValueError('Switch ACK device identity mismatch')
    return raw
