"""Sense GATT v1: nonce-bound 86-byte authenticated, age-qualified snapshot.

32-byte per-device keys are operator-provisioned only. This module never sends,
generates or saves an enrollment key. Challenge nonces are ephemeral, one-use.
"""
from __future__ import annotations
import asyncio
from dataclasses import replace
import hashlib
import hmac
import math
import os
from pathlib import Path
import secrets
import stat
import struct
import time
from adapters import PresenceAdapter, event, reading
from store import EdgeStore
from contract import PRESENCE_GATT

SERVICE_UUID = PRESENCE_GATT['service_uuid']
CHALLENGE_UUID = PRESENCE_GATT['challenge_uuid']
RESPONSE_UUID = PRESENCE_GATT['response_uuid']
DOMAIN = bytes.fromhex(PRESENCE_GATT['mac_domain_hex'])
RESPONSE_SIZE = PRESENCE_GATT['response_bytes']
UNKNOWN_AGE = PRESENCE_GATT['unknown_age']


def load_key(path):
    if not path:
        raise ValueError('operator-provisioned per-device authentication key is required')
    if os.name != 'posix':
        raise ValueError('authenticated Sense enrollment requires a POSIX host with verified private key permissions')
    info = os.stat(path)
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
        raise ValueError('authentication key must be a private regular file (0600/0400)')
    data = Path(path).read_bytes()
    if len(data) != 32:
        raise ValueError('authentication key must contain exactly 32 binary bytes')
    return data


class ChallengeVerifier:
    def __init__(self, key, clock=time.monotonic):
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError('32-byte enrollment key required')
        self.key = key
        self.clock = clock
        self.pending = None

    def challenge(self):
        nonce = secrets.token_bytes(16)
        started = self.clock()
        self.pending = (nonce, started, started + 5.0)
        return nonce

    def verify(self, response):
        pending, self.pending = self.pending, None  # Every attempt consumes the challenge.
        if pending is None or self.clock() > pending[2]:
            raise ValueError('no outstanding fresh authentication challenge')
        if not isinstance(response, bytes) or len(response) != RESPONSE_SIZE or response[0] != 1:
            raise ValueError('invalid authenticated response format')
        body, mac = response[:54], response[54:]
        if not hmac.compare_digest(body[25:41], pending[0]):
            raise ValueError('authentication challenge mismatch')
        if not hmac.compare_digest(mac, hmac.digest(self.key, DOMAIN + body, 'sha256')):
            raise ValueError('authentication MAC mismatch')
        raw = PresenceAdapter.parse_v2(body[1:25])
        pir_age, radar_age, light_age = struct.unpack('<III', body[41:53])
        flags = body[53]
        if flags & ~31 or flags & 2 or pir_age != UNKNOWN_AGE:
            raise ValueError('reserved evidence flag')
        for bit, age in ((2, pir_age), (4, radar_age), (8, light_age)):
            if flags & bit and age == UNKNOWN_AGE:
                raise ValueError('valid measurement has unknown age')
        if self.clock() > pending[2]:
            raise ValueError('authentication challenge expired during verification')
        return raw, {'pir_age_ms': pir_age, 'radar_age_ms': radar_age, 'light_age_ms': light_age, 'evidence_flags': flags, 'challenge_round_trip_ms': max(0, math.ceil((self.clock() - pending[1]) * 1000))}, body[1:25]


def authenticated_event(enrollment, response, verifier, now=None):
    now = time.time() if now is None else now
    raw, ages, frame = verifier.verify(response)
    if raw['identity'] != enrollment.ble_identity or enrollment.protocol != 'presence-gatt-v1':
        raise ValueError('authenticated device identity/protocol mismatch')
    diagnostics = PresenceAdapter.telemetry(replace(enrollment, protocol='presence-ble-v2'), frame, now)
    flags = ages['evidence_flags']
    readings = []
    continuous = bool(flags & 1)
    for r in diagnostics['readings']:
        r = {**r, 'details': {**r.get('details', {}), 'authenticity': 'authenticated_gatt_hmac_sha256'}}
        cap = r['capability']
        if cap in {'presence.pir', 'presence.radar', 'illuminance.raw'}:
            key, bit, max_age = {'presence.pir': ('pir_age_ms', 2, 5000), 'presence.radar': ('radar_age_ms', 4, 5000), 'illuminance.raw': ('light_age_ms', 8, 120000)}[cap]
            age = ages[key]
            bounded_age = age + ages['challenge_round_trip_ms'] if age != UNKNOWN_AGE else UNKNOWN_AGE
            valid = bool(flags & bit) and bounded_age <= max_age
            r['details']['measurement_age_ms'] = None if age == UNKNOWN_AGE else bounded_age
            if not valid:
                r['value'], r['quality'] = None, 'unknown'
            elif r['value'] is not None and cap == 'presence.radar':
                r['quality'] = 'valid' if continuous else 'partial'
                r['details'].update(continuous_occupancy=continuous, sample_only=not continuous)
        elif cap == 'buffer.voltage' and not flags & 16:
            r['value'], r['quality'] = None, 'unknown'
        readings.append(r)
    # Store proof digest, never the enrollment secret. Raw signed response is retained
    # for post-mortem verification with the operator's separate key custody.
    evidence = {**diagnostics['raw'], **ages, 'response_hex': response.hex(),
        'authentication': 'hmac-sha256-nonce-v1', 'proof_sha256': hashlib.sha256(response).hexdigest()}
    return event(enrollment, f'{raw["boot"]:08x}', raw['sample_seq'], now, raw['monotonic_s'] * 1000,
        readings, evidence, quality='valid' if all(r['quality'] in {'valid', 'uncalibrated'} for r in readings) else 'partial')


async def fetch_authenticated(enrollment, database, client_factory=None, now=None):
    if client_factory is None:
        from bleak import BleakClient
        client_factory = BleakClient
    key = load_key(enrollment.auth_key_file)
    verifier = ChallengeVerifier(key)
    store = EdgeStore(database)
    try:
        async with client_factory(enrollment.ble_address, timeout=10) as client:
            nonce = verifier.challenge()
            await asyncio.wait_for(client.write_gatt_char(CHALLENGE_UUID, nonce, response=True), timeout=2)
            response = bytes(await asyncio.wait_for(client.read_gatt_char(RESPONSE_UUID), timeout=2))
            value = authenticated_event(enrollment, response, verifier, now)
            receipt = store.accept_event(value, authenticated=True)
            store.health('gatt:' + enrollment.device_id, {'status': 'authenticated', 'boot_id': value['boot_id'], 'sequence': value['sequence']})
            return receipt
    except Exception as error:
        store.health('gatt:' + enrollment.device_id, {'status': 'unavailable', 'error': type(error).__name__})
        raise
    finally:
        store.close()
