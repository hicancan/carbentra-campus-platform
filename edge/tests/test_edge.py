import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from fixtures import *
from ingress import Ingress
from service import strict_json
from store import EdgeStore
from contract import validate_event, validate_descriptor, validate_command
from adapters import descriptor

class EdgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=str(Path(self.tmp.name)/'edge.sqlite')
        self.store=EdgeStore(self.db);self.ingress=Ingress(self.store,[PLUG,SWITCH,SENSE])
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_strict_json_rejects_duplicate_nonfinite_large_deep(self):
        for text in ['{"a":1,"a":2}','{"a":NaN}','{"a":1e999}','{"a":'+('9'*4000)+'}', '['*2000+'0'+']'*2000]:
            with self.subTest(text=text[:20]),self.assertRaises(ValueError):strict_json(text)
    def test_exact_topics_enrollment_retained_and_time_nonce(self):
        with self.assertRaises(ValueError):self.ingress.mqtt('carbentra/v1/EVIL/hello','{}')
        with self.assertRaises(ValueError):self.ingress.mqtt('carbentra/switch/'+PLUG.device_id+'/state','{}')
        self.assertIsNone(self.ingress.mqtt('evil/topic','garbage',retained=True))
        topic,data=self.ingress.mqtt(f'carbentra/v1/{PLUG.device_id}/hello',json.dumps({'clock_nonce':'a'*32}),now=NOW)
        self.assertEqual(data['unix_s'],int(NOW));self.assertTrue(topic.endswith('/time'))
    def test_durable_sample_receipt_dedup_first_arrival_conflict(self):
        topic=f'carbentra/v1/{PLUG.device_id}/telemetry';raw=plug_raw()
        result=self.ingress.mqtt(topic,json.dumps(raw),now=NOW)
        self.assertEqual(result[1]['sample_seq'],'1')
        self.ingress.mqtt(topic,json.dumps(dict(reversed(list(raw.items())))),now=NOW+4)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM iot_events').fetchone()[0],1)
        self.assertEqual(self.store.status()['outbox_pending'],1)
        self.assertEqual(self.store.snapshot(PLUG.device_id,NOW+4)['age_seconds'],4)
        raw['desired_on']=False
        with self.assertRaises(ValueError):self.ingress.mqtt(topic,json.dumps(raw),now=NOW+5)
    def test_atomic_raw_outbox_rollback(self):
        self.store.db.execute('DROP TABLE forwarding');self.store.db.commit()
        with self.assertRaises(sqlite3.Error):self.store.accept_event(PlugAdapter.telemetry(PLUG,plug_raw(),NOW))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM iot_events').fetchone()[0],0)
    def test_restart_offline_cache_staleness_and_out_of_order(self):
        self.store.accept_event(SwitchAdapter.telemetry(SWITCH,switch_raw(seq=2),NOW))
        self.store.accept_event(SwitchAdapter.telemetry(SWITCH,switch_raw(seq=1,on=True),NOW+1))
        self.assertEqual(self.store.snapshot(SWITCH.device_id,NOW+1)['event']['sequence'],'2')
        self.store.close();self.store=EdgeStore(self.db)
        self.assertFalse(self.store.snapshot(SWITCH.device_id,NOW+20)['fresh'])
        self.assertTrue(self.store.snapshot(SWITCH.device_id,NOW-1)['clock_reversed'])
    def test_retired_boot_never_replaces_current(self):
        for raw in [switch_raw(1,'b'*32),switch_raw(1,'c'*32),switch_raw(2,'b'*32)]:
            self.store.accept_event(SwitchAdapter.telemetry(SWITCH,raw,NOW))
        self.assertEqual(self.store.snapshot(SWITCH.device_id,NOW)['event']['boot_id'],'c'*32)
    def test_switch_channels_are_independent_aggregate_not_split(self):
        value=SwitchAdapter.telemetry(SWITCH,switch_raw(),NOW)
        feedback=[r for r in value['readings'] if r['capability']=='relay.feedback']
        self.assertEqual(len(feedback),3);self.assertTrue(all(r['value'] is None for r in feedback))
        self.assertEqual([r['channel_id'] for r in value['readings'] if r['capability']=='energy.import'],['meter.aggregate'])
        for mutation in ['feedback','duplicate','identity','raw_number','freshness']:
            raw=switch_raw()
            if mutation=='feedback':raw['channels'][0]['physically_verified_on']=True
            if mutation=='duplicate':raw['channels'][1]=raw['channels'][0]
            if mutation=='identity':raw['sample_seq']='01'
            if mutation=='raw_number':raw['aggregate_meter']['active_power_w']=float('nan')
            if mutation=='freshness':raw['aggregate_meter']['observed_uptime_ms']='0'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):SwitchAdapter.telemetry(SWITCH,raw,NOW)
    def test_contract_identity_unit_truth_bounds_and_leases(self):
        original=SwitchAdapter.telemetry(SWITCH,switch_raw(),NOW)
        for mutate in [lambda x:x.update(event_id='0'*64),lambda x:x['readings'][0].update(unit='W'),lambda x:x['readings'][0].update(value=None),lambda x:x['raw'].update(sample_seq='20'),lambda x:x.update(observed_at=iso(NOW))]:
            value=copy.deepcopy(original);mutate(value)
            with self.assertRaises(ValueError):validate_event(value)
        for e in (PLUG,SWITCH,SENSE):validate_descriptor(descriptor(e))
        cmd=command();cmd['expires_at']=iso(NOW+31)
        with self.assertRaises(ValueError):validate_command(cmd)
