import copy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from fixtures import *
from rules import RuleEngine
from store import EdgeStore

class RuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=str(Path(self.tmp.name)/'edge.sqlite');self.store=EdgeStore(self.db)
        self.engine=RuleEngine(self.db)
        self.rule={'id':'room-a101-presence','sensor_device_id':SENSE.device_id,'target_device_id':SWITCH.device_id,
            'channel_id':'relay.1','when_present':True,'desired_on':True,'stable_for_seconds':0,'maximum_age_seconds':5,
            'lease':{'lease_id':'fixture-local-lease','issuer':'operator','issued_at':iso(NOW-1),'expires_at':iso(NOW+100),'offline_until':iso(NOW+50),'sequence_start':'100','sequence_end':'110'}}
        self.bundle={'schema_version':1,'revision':1,'valid_until':iso(NOW+200),'rules':[self.rule]}
        self.engine.install(self.bundle);self.feed(1,NOW)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def feed(self,seq,now,radar=2,on=False):
        self.store.accept_event(sense_event(seq,now,radar),authenticated=True)
        self.store.accept_event(SwitchAdapter.telemetry(SWITCH,switch_raw(seq,on=on,uptime_ms=100000+int((now-NOW)*1000)),now))
    def test_bounded_virtual_candidate_and_no_replay(self):
        result=self.engine.once(now=NOW)[0];self.assertEqual(result['reason'],'authorized_candidate')
        self.assertEqual(result['command']['sequence'],'100');self.assertEqual(result['command']['channel_id'],'relay.1')
        self.assertEqual(self.engine.once(now=NOW)[0]['reason'],'sample_already_evaluated_no_replay')
        self.engine=RuleEngine(self.db)
        self.assertEqual(self.engine.once(now=NOW)[0]['reason'],'sample_already_evaluated_no_replay')
    def test_manual_fault_stale_expiry_do_not_dispatch(self):
        self.assertEqual(self.engine.once(now=NOW+6)[0]['reason'],'target_unknown_or_stale')
        self.feed(2,NOW+51)
        self.assertEqual(self.engine.once(now=NOW+51)[0]['reason'],'authority_expired_or_not_started')
        raw=switch_raw(3,uptime_ms=152000);raw['channels'][0]['control_mode']='manual'
        self.store.accept_event(SwitchAdapter.telemetry(SWITCH,raw,NOW+52))
        self.assertEqual(self.engine.once(now=NOW+52)[0]['reason'],'manual_or_maintenance_or_protected')
    def test_untrusted_real_broadcast_never_authorizes(self):
        # Real target + real untrusted diagnostic sensor cannot be promoted to trusted evidence.
        real_target=replace(SWITCH,source_mode='REAL');real_sensor=replace(SENSE,source_mode='REAL',protocol='presence-ble-v2')
        raw=switch_raw(2);raw['source_mode']='REAL'
        self.store.accept_event(SwitchAdapter.telemetry(real_target,raw,NOW+1))
        ev=PresenceAdapter.telemetry(real_sensor,presence_frame(2),NOW+1)
        # Current trusted SIMULATED event remains a different-source observation and is denied.
        self.store.accept_event(ev)
        self.assertIn(self.engine.once(now=NOW+1)[0]['reason'],{'continuous_occupancy_evidence_unavailable','unauthenticated_or_mixed_source_evidence'})
    def test_explicit_absence_requires_60s_continuous_fresh_evidence(self):
        bundle=copy.deepcopy(self.bundle);bundle['revision']=2;rule=bundle['rules'][0]
        rule.update(when_present=False,desired_on=False,stable_for_seconds=60)
        rule['lease']['offline_until']=iso(NOW+99)
        rule['lease']['lease_id']='absence-lease'
        self.engine.install(bundle)
        for i in range(16):
            now=NOW+i*4;self.feed(i+2,now,radar=1,on=True)
            result=self.engine.once(now=now)[0]
            self.assertEqual(result['reason'],'authorized_candidate' if i==15 else 'waiting_for_stable_evidence')
        self.assertFalse(result['command']['value'])
    def test_no_lease_shadow_and_revision_rollback_conflict(self):
        bundle=copy.deepcopy(self.bundle);bundle['revision']=2;del bundle['rules'][0]['lease']
        self.engine.install(bundle);self.assertEqual(self.engine.once(now=NOW)[0]['reason'],'evaluated_not_authorized')
        with self.assertRaises(ValueError):self.engine.install(self.bundle)
        bundle['rules'][0]['desired_on']=False
        with self.assertRaises(ValueError):self.engine.install(bundle)
    def test_expired_policy_and_false_never_mean_unknown(self):
        result=self.engine.once(now=NOW+201)[0];self.assertEqual(result['reason'],'policy_expired')
        self.feed(2,NOW+1,radar=0)
        self.assertEqual(self.engine.once(now=NOW+1)[0]['reason'],'continuous_occupancy_evidence_unavailable')
