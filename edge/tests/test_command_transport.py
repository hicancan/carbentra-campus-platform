from contextlib import closing
import datetime
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from command_transport import CommandTransport,wire_command

class CommandTransportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=str(Path(self.tmp.name)/'edge.sqlite');self.published=[];self.reported=[]
  def publish(topic,payload):self.published.append((topic,payload));return True
  self.transport=CommandTransport(self.db,['virtual-unit'],['virtual-unit'],publish,reporter=lambda *args:self.reported.append(args))
  self.item={'id':'cmd-001','device_id':'virtual-unit','source_mode':'SIMULATED','dispatch_mode':'VIRTUAL','transport':'MQTT','wire':{'id':'cmd-001','device_id':'virtual-unit','profile_id':'lab-load','seq':'1','issued_s':1800000000,'expires_s':1800000030,'action':'shed'},'lease_id':'synthetic-lease','lease_expires_at':datetime.datetime.fromtimestamp(1800000020,datetime.timezone.utc).isoformat()}
 def tearDown(self):self.tmp.cleanup()
 def test_published_not_verified_and_no_duplicate_send(self):
  a=self.transport.process(self.item,1800000001);self.assertEqual(a['status'],'published');self.assertEqual(len(self.published),1)
  self.transport.process({**self.item,'lease_id':'new-lease'},1800000002);self.assertEqual(len(self.published),1);self.assertEqual(len(self.reported),2)
  self.assertEqual(json.loads(self.published[0][1]),self.item['wire'])
 def test_physical_unallowlisted_expired_and_future_never_publish(self):
  changes=[{'source_mode':'REAL'},{'dispatch_mode':'PHYSICAL'},{'transport':'HTTP'},{'lease_expires_at':'2020-01-01T00:00:00+00:00'}]
  for index,change in enumerate(changes):
   item={**self.item,**change,'id':f'cmd-{index+2}','wire':{**self.item['wire'],'id':f'cmd-{index+2}','seq':str(index+2)}}
   self.assertNotEqual(self.transport.process(item,1800000001)['status'],'published')
  self.assertEqual(self.transport.process(self.item,1799999999)['reason'],'future_command');self.assertEqual(self.published,[])
 def test_crash_before_or_after_publish_never_blind_replays(self):
  with closing(sqlite3.connect(self.db)) as db, db:db.execute('INSERT INTO command_inbox VALUES(?,?,?,?,?,?,?)',('cmd-001','virtual-unit','1',wire_command(self.item['wire'],'virtual-unit'),'sending',None,1800000000))
  result=self.transport.process(self.item,1800000001);self.assertEqual(result['reason'],'mqtt_delivery_uncertain');self.assertEqual(self.published,[])
 def test_mqtt_uncertainty_and_older_sequence(self):
  self.transport.publisher=lambda *_:False
  self.assertEqual(self.transport.process(self.item,1800000001)['reason'],'mqtt_delivery_uncertain')
  self.transport.publisher=lambda *_:self.fail('must not replay')
  self.transport.process(self.item,1800000002)
  old={**self.item,'id':'cmd-002','wire':{**self.item['wire'],'id':'cmd-002'}}
  self.assertEqual(self.transport.process(old,1800000002)['reason'],'replayed_sequence')
 def test_id_conflict_preserves_original(self):
  self.transport.process(self.item,1800000001)
  changed={**self.item,'wire':{**self.item['wire'],'action':'restore'}}
  self.assertEqual(self.transport.process(changed,1800000002)['reason'],'conflicting_command_identity');self.assertEqual(len(self.published),1)
 def test_delivery_report_failure_retries_receipt_only(self):
  self.transport.reporter=lambda *_:(_ for _ in ()).throw(OSError('platform offline'))
  with self.assertRaises(OSError):self.transport.process(self.item,1800000001)
  self.transport.reporter=lambda *args:self.reported.append(args)
  self.transport.process(self.item,1800000002);self.assertEqual(len(self.published),1)
 def test_canonical_command_rejects_bad_sequence_and_extra_fields(self):
  for change in [{'seq':'01'},{'seq':'18446744073709551616'},{'seq':1},{'action':'toggle'},{'expires_s':1800000061},{'issued_s':True},{'schema_version':2}]:
   with self.assertRaises(ValueError):wire_command({**self.item['wire'],**change},'virtual-unit')
 def test_default_has_no_dispatch(self):
  other=CommandTransport(self.db,['virtual-unit'],[],lambda *_:self.fail('disabled'),reporter=lambda *_:None)
  self.assertEqual(other.once(),0);self.assertEqual(other.process(self.item,1800000001)['status'],'failed')
 def test_physical_path_inert_callback_requires_independent_release(self):
  # No MQTT client, credentials, hardware or operational flag is enabled.
  calls=[];reports=[]
  physical=CommandTransport(self.db,['physical-unit'],[],lambda topic,payload:calls.append((topic,payload)) or True,reporter=lambda *args:reports.append(args),physical_enabled=True,physical_releases={'physical-unit':'release-lab-attestation'})
  item={**self.item,'device_id':'physical-unit','source_mode':'REAL','dispatch_mode':'PHYSICAL','release_id':'release-lab-attestation','wire':{**self.item['wire'],'device_id':'physical-unit'}}
  self.assertEqual(physical.process(item,1800000001)['status'],'published');self.assertEqual(len(calls),1)
  for index,change in enumerate([{'release_id':'wrong'},{'source_mode':'SIMULATED'},{'dispatch_mode':'VIRTUAL'}]):
   candidate={**item,**change,'id':f'blocked-{index}','wire':{**item['wire'],'id':f'blocked-{index}','seq':str(index+2)}}
   self.assertEqual(physical.process(candidate,1800000002)['status'],'failed')
  disabled=CommandTransport(self.db,['physical-unit'],[],lambda *_:self.fail('disabled physical publisher'),reporter=lambda *_:None,physical_releases={'physical-unit':'release-lab-attestation'})
  new={**item,'id':'disabled-001','wire':{**item['wire'],'id':'disabled-001','seq':'10'}}
  self.assertEqual(disabled.process(new,1800000002)['status'],'failed');self.assertEqual(len(calls),1)
 def test_physical_enablement_never_uses_truthiness(self):
  for enabled,releases in [('false',{'physical-unit':'release'}),(True,{}),(True,{'unallowlisted':'release'}),(True,{'physical-unit':True})]:
   with self.assertRaises(ValueError):CommandTransport(self.db,['physical-unit'],[],lambda *_:True,physical_enabled=enabled,physical_releases=releases)
if __name__=='__main__':unittest.main()
