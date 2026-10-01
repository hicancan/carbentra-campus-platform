"""The actual firmware JSON encoder is compiled with safe host drivers, then
passed to the same schema/SQLite path as a real device. No physical IO occurs.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from store import EdgeStore
from ingress import Ingress
from adapters import Enrollment

class FirmwareWireTests(unittest.TestCase):
 def test_actual_switch_decoder_and_canonical_command_id_boundaries(self):
  from channel_transport import ChannelTransport
  from contract import validate_command
  from fixtures import SWITCH, NOW, SwitchAdapter, command, switch_raw
  import tempfile
  executable=os.environ.get('CARBENTRA_SWITCH_COMMAND_TEST_BINARY')
  if not executable:self.skipTest('Switch command decoder host binary not supplied; separately required integration gate')
  with tempfile.TemporaryDirectory() as directory:
   database=str(Path(directory)/'edge.sqlite');store=EdgeStore(database)
   try:
    store.accept_event(SwitchAdapter.telemetry(SWITCH,switch_raw(),NOW))
    published=[];transport=ChannelTransport(database,[SWITCH],lambda *args:published.append(args) or True,enable_virtual=True)
    cmd=command();cmd['id']='a'*48
    validate_command(cmd)
    self.assertEqual(transport.process(cmd,NOW)['status'],'published')
    wire=json.loads(published[0][1])
    self.assertEqual(subprocess.run([executable,json.dumps(wire)],capture_output=True,text=True).returncode,0)
    for invalid in ('a'*49, 'id\n', ''):
     cmd['id']=invalid;wire['id']=invalid
     with self.subTest(id=repr(invalid)):
      with self.assertRaises(ValueError):validate_command(cmd)
      with self.assertRaises(ValueError):transport.process(cmd,NOW)
      self.assertEqual(subprocess.run([executable,json.dumps(wire)],capture_output=True,text=True).returncode,1)
    self.assertEqual(len(published),1)
   finally:store.close()

 def test_actual_firmware_encoding(self):
  executable=os.environ.get('CARBENTRA_STARTUP_TEST_BINARY')
  if not executable:self.skipTest('firmware startup host binary not supplied; separately required integration gate')
  result=subprocess.run([executable,'0'],env={**os.environ,'CARBENTRA_DUMP_WIRE':'1'},capture_output=True,text=True,check=True)
  store=EdgeStore(':memory:');edge=Ingress(store,[Enrollment('CM-001122334455','PLUG','plug-wire-v2')]);telemetry=acks=0
  try:
   for line in result.stdout.splitlines():
    if line.startswith('WIRE '):
     topic,receipt=edge.mqtt('carbentra/v1/CM-001122334455/telemetry',line[5:]);self.assertEqual(receipt['sample_seq'],str(telemetry+1));telemetry+=1
    if line.startswith('ACK '):edge.mqtt('carbentra/v1/CM-001122334455/ack',line[4:]);acks+=1
   self.assertEqual((telemetry,acks),(2,2))
   saved=[json.loads(row[0])['raw'] for row in store.db.execute('SELECT payload FROM iot_events ORDER BY sequence')]
   self.assertIsNone(saved[0]['unix_s']);self.assertEqual(saved[1]['unix_s'],1800000002);self.assertEqual(saved[1]['known_forward_wh_since_boot'],12.5)
   acknowledged=[json.loads(row[0]) for row in store.db.execute('SELECT payload FROM wire_acks ORDER BY rowid')]
   self.assertFalse(acknowledged[0]['terminal']);self.assertEqual(acknowledged[1]['status'],'OBSERVED_VERIFIED');self.assertEqual(acknowledged[0]['id'],acknowledged[1]['id']);self.assertEqual(acknowledged[0]['seq'],acknowledged[1]['seq'])
  finally:store.close()
if __name__=='__main__':unittest.main()
