from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from fixtures import *
from channel_transport import ChannelTransport
from contract import canonical
from store import EdgeStore

class ChannelTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=str(Path(self.tmp.name)/'edge.sqlite')
        self.store=EdgeStore(self.db);self.store.accept_event(SwitchAdapter.telemetry(SWITCH,switch_raw(),NOW))
        self.published=[];self.transport=ChannelTransport(self.db,[SWITCH],lambda *x:self.published.append(x) or True,enable_virtual=True)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_single_channel_translation_and_no_blind_duplicate(self):
        cmd=command();cmd['channel_id']='relay.2'
        self.assertEqual(self.transport.process(cmd,NOW)['status'],'published')
        topic,payload=self.published[0];wire=json.loads(payload)
        self.assertEqual(wire['channel'],2);self.assertEqual(wire['expires_uptime_ms'],'120000')
        self.assertTrue(topic.endswith('/command'))
        self.assertEqual(self.transport.process(cmd,NOW+1)['status'],'published');self.assertEqual(len(self.published),1)
    def test_default_off_physical_off_and_stale(self):
        disabled=ChannelTransport(self.db,[SWITCH],lambda *_:self.fail('disabled'))
        self.assertEqual(disabled.process(command(),NOW)['reason'],'virtual_dispatch_disabled')
        real=replace(SWITCH,source_mode='REAL');cmd=command(device=real,seq=2)
        real_transport=ChannelTransport(self.db,[real],lambda *_:self.fail('physical disabled'))
        self.assertEqual(real_transport.process(cmd,NOW)['reason'],'physical_release_not_allowlisted')
        self.assertEqual(self.transport.process(command(seq=3),NOW+11)['reason'],'fresh_observation_required')
    def test_manual_hold_maintenance_fault_unknown_priority(self):
        for seq,mode in enumerate(['manual','maintenance','protected'],start=2):
            raw=switch_raw(seq=seq);raw['channels'][0]['control_mode']=mode
            self.store.accept_event(SwitchAdapter.telemetry(SWITCH,raw,NOW))
            self.assertEqual(self.transport.process(command(seq=seq),NOW)['reason'],'manual_or_protected_or_unknown')
        self.assertEqual(self.published,[])
    def test_expired_wrong_boot_sequence_and_restart_uncertainty(self):
        self.assertEqual(self.transport.process(command(),NOW+21)['status'],'expired')
        self.assertEqual(self.transport.process(command(seq=2,boot='c'*32),NOW)['reason'],'boot_or_source_changed')
        cmd=command(seq=3)
        with closing(sqlite3.connect(self.db)) as db, db:db.execute('INSERT INTO command_inbox VALUES(?,?,?,?,?,?,?)',(cmd['id'],SWITCH.device_id,'3',canonical({k:v for k,v in cmd.items() if k not in {'authority','expires_at'}}),'sending',None,NOW))
        self.assertEqual(self.transport.process(cmd,NOW)['reason'],'mqtt_delivery_uncertain')
        self.assertEqual(self.published,[])
    def test_publish_failure_never_retried_and_conflict_never_replaced(self):
        self.transport.publisher=lambda *_:False
        cmd=command();self.assertEqual(self.transport.process(cmd,NOW)['reason'],'mqtt_delivery_uncertain')
        self.transport.publisher=lambda *_:self.fail('must not replay')
        self.assertEqual(self.transport.process(cmd,NOW)['reason'],'mqtt_delivery_uncertain')
        changed={**cmd,'value':False};self.assertEqual(self.transport.process(changed,NOW)['reason'],'conflicting_command_identity')

    def test_backend_edge_manual_hold_persists_and_does_not_modify_wire(self):
        cmd=command();cmd['authority']['kind']='manual';cmd['manual_hold_seconds']=60
        self.assertEqual(self.transport.process(cmd,NOW)['status'],'published')
        wire=json.loads(self.published[0][1]);self.assertEqual(set(wire),{'id','boot_id','seq','channel','on','expires_uptime_ms'})
        held=self.store.active_manual_hold(SWITCH.device_id,'relay.1',NOW+1)
        self.assertTrue(held['active']);self.assertFalse(self.store.active_manual_hold(SWITCH.device_id,'relay.2',NOW+1)['active'])
        self.assertEqual(self.transport.process(command(seq=2),NOW+1)['reason'],'backend_edge_manual_hold')
        restored=ChannelTransport(self.db,[SWITCH],lambda *_:True,enable_virtual=True)
        self.assertEqual(restored.process(command(seq=3),NOW+2)['reason'],'backend_edge_manual_hold')

    def test_expiry_rechecked_after_sqlite_before_publish(self):
        from unittest.mock import patch
        with patch('channel_transport.time.monotonic',side_effect=[100.0,121.0]):
            self.assertEqual(self.transport.process(command(),NOW)['status'],'expired')
        self.assertEqual(self.published,[])
