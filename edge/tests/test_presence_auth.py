import asyncio
from dataclasses import replace
import hashlib
import hmac
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from fixtures import *
from adapters import descriptor
from presence_auth import *
from store import EdgeStore
from ble_scanner import scan

class PresenceAuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name);self.db=str(self.path/'edge.sqlite')
        self.store=EdgeStore(self.db)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_vector_matches_full_mac_and_firmware_layout(self):
        path=Path(__file__).resolve().parents[2]/'packages/iot-contract/examples/presence-gatt-v1-test-vector.json'
        vector=json.loads(path.read_text(encoding="utf-8"));response=bytes.fromhex(vector['response_hex'])
        self.assertEqual(len(response),86)
        self.assertEqual(response,signed_response(bytes.fromhex(vector['nonce_hex']),seq=2,radar=1))
        verifier=ChallengeVerifier(TEST_KEY);verifier.pending=(bytes.fromhex(vector['nonce_hex']),time.monotonic(),time.monotonic()+5)
        value=authenticated_event(SENSE,response,verifier,NOW)
        radar=next(r for r in value['readings'] if r['capability']=='presence.radar')
        self.assertEqual(radar['value'],False);self.assertEqual(radar['quality'],'valid')
        self.assertIsNone(value['observed_at']);self.assertNotIn('key',value['raw'])
        self.assertFalse(any(r['capability']=='presence.pir' for r in value['readings']))
    def test_mac_nonce_expiry_and_one_use(self):
        clock=[1.0]
        for kind in ('mac','nonce','expired','version','truncated'):
            v=ChallengeVerifier(TEST_KEY,clock=lambda:clock[0]);nonce=v.challenge();response=signed_response(nonce)
            if kind=='mac':response=response[:-1]+bytes([response[-1]^1])
            if kind=='nonce':response=signed_response(b'X'*16)
            if kind=='expired':clock[0]+=6
            if kind=='version':response=b'\x02'+response[1:]
            if kind=='truncated':response=response[:-1]
            with self.subTest(kind=kind),self.assertRaises(ValueError):v.verify(response)
            with self.assertRaises(ValueError):v.verify(signed_response(nonce))
        v=ChallengeVerifier(TEST_KEY);nonce=v.challenge();v.verify(signed_response(nonce))
        with self.assertRaises(ValueError):v.verify(signed_response(nonce))
    def test_unknown_driver_bad_age_and_noncontinuous_cannot_prove_vacancy(self):
        for evidence,age in [(28,100),(29,6000),(25,UNKNOWN_AGE)]:
            v=ChallengeVerifier(TEST_KEY);nonce=v.challenge()
            value=authenticated_event(SENSE,signed_response(nonce,radar=1,ages=(UNKNOWN_AGE,age,1),evidence=evidence),v,NOW)
            radar=next(r for r in value['readings'] if r['capability']=='presence.radar')
            self.assertNotEqual(radar['quality'],'valid')
    def test_broadcast_is_diagnostic_and_reserved_pir_rejected(self):
        e=replace(SENSE,protocol='presence-ble-v2')
        value=PresenceAdapter.telemetry(e,presence_frame(radar=1),NOW)
        radar=next(r for r in value['readings'] if r['capability']=='presence.radar')
        self.assertEqual(radar['quality'],'partial');self.assertFalse(radar['details']['continuous_occupancy'])
        with self.assertRaises(ValueError):PresenceAdapter.telemetry(e,presence_frame(flags=193),NOW)
        self.assertFalse(any(c['channel_id']=='sensor.pir' for c in descriptor(e)['channels']))
    def test_durable_replay_and_spoofed_broadcast_cannot_retire_authenticated_boot(self):
        value=sense_event();self.store.accept_event(value,authenticated=True)
        spoof=PresenceAdapter.telemetry(replace(SENSE,protocol='presence-ble-v2'),presence_frame(seq=500,boot=3),NOW+1)
        self.store.accept_event(spoof)
        self.assertEqual(self.store.snapshot(SENSE.device_id,NOW+1)['event']['source_protocol'],'presence-gatt-v1')
        self.store.close();self.store=EdgeStore(self.db)
        with self.assertRaises(ValueError):self.store.accept_event(value,authenticated=True)
        self.store.accept_event(sense_event(seq=2,now=NOW+2),authenticated=True)
        # Authenticated boot transition permanently retires previous authenticated session.
        v=ChallengeVerifier(TEST_KEY);nonce=v.challenge()
        value2=authenticated_event(SENSE,signed_response(nonce,boot=99),v,NOW+3)
        self.store.accept_event(value2,authenticated=True)
        with self.assertRaises(ValueError):self.store.accept_event(sense_event(seq=3,now=NOW+4),authenticated=True)
    @unittest.skipUnless(os.name == 'posix', 'POSIX private-key permissions are verified in the Linux suite')
    def test_missing_or_public_key_files_fail_closed(self):
        with self.assertRaises(ValueError):load_key(None)
        key=self.path/'test.key';key.write_bytes(TEST_KEY);key.chmod(0o644)
        with self.assertRaises(ValueError):load_key(key)
        key.chmod(0o600);self.assertEqual(load_key(key),TEST_KEY)
    @unittest.skipUnless(os.name == 'posix', 'Authenticated Sense enrollment uses POSIX private-key permissions')
    def test_bleak_client_write_read_works_with_protocol_fake_no_radio_claim(self):
        key=self.path/'test.key';key.write_bytes(TEST_KEY);key.chmod(0o600)
        enrollment=replace(SENSE,auth_key_file=str(key))
        calls=[]
        class Client:
            def __init__(self,address,timeout):calls.append(('connect',address,timeout))
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def write_gatt_char(self,uuid,value,response):
                self.nonce=value;calls.append(('write',uuid,response))
            async def read_gatt_char(self,uuid):calls.append(('read',uuid));return signed_response(self.nonce)
        receipt=asyncio.run(fetch_authenticated(enrollment,self.db,Client,now=NOW))
        self.assertTrue(receipt['durable']);self.assertEqual(calls[1][1],CHALLENGE_UUID);self.assertEqual(calls[2][1],RESPONSE_UUID)
    @unittest.skipIf(os.name == 'posix', 'Non-POSIX startup guard')
    def test_non_posix_key_loading_fails_closed(self):
        key = self.path/'test.key'
        key.write_bytes(TEST_KEY)
        with self.assertRaisesRegex(ValueError, 'POSIX host'):
            load_key(key)
    def test_bleak_scanner_callback_parser_store_with_fake_no_radio(self):
        stop=threading.Event();real=replace(SENSE,source_mode='REAL',protocol='presence-ble-v2')
        class Scanner:
            def __init__(self,**options):self.callback=options['detection_callback']
            async def __aenter__(self):
                self.callback(SimpleNamespace(address=real.ble_address),SimpleNamespace(manufacturer_data={65535:presence_frame()}))
                asyncio.get_running_loop().call_later(.05,stop.set)
                return self
            async def __aexit__(self,*args):pass
        asyncio.run(scan(self.db,[real],stop,scanner_factory=Scanner))
        self.assertEqual(self.store.status()['outbox_pending'],1)

    def test_unsigned_tuple_cannot_poison_later_authenticated_sample(self):
        # Same wire device/boot/seq, but diagnostic identity has an explicit domain.
        unsigned=PresenceAdapter.telemetry(replace(SENSE,protocol='presence-ble-v2'),presence_frame(seq=1,radar=1),NOW)
        self.assertTrue(unsigned['boot_id'].startswith('adv-'))
        self.store.accept_event(unsigned)
        signed=sense_event(seq=1,now=NOW+1,radar=2)
        self.store.accept_event(signed,authenticated=True)
        self.assertEqual(self.store.snapshot(SENSE.device_id,NOW+1)['event']['source_protocol'],'presence-gatt-v1')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM iot_events').fetchone()[0],2)

    def test_gatt_enrolled_broadcasts_are_diagnostics_only_not_cloud_observations(self):
        from ingress import Ingress
        real=replace(SENSE,source_mode='REAL')
        ingress=Ingress(self.store,[real])
        receipt=ingress.ble(real.ble_address,{65535:presence_frame(seq=4000000000)},NOW)
        self.assertTrue(receipt['diagnostic_only'])
        self.assertEqual(self.store.status()['outbox_pending'],0)
        self.assertIsNone(self.store.snapshot(real.device_id,NOW))
