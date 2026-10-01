import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from platform_forwarder import Forwarder
from store import EdgeStore
from fixtures import *

class ForwarderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.database=str(Path(self.tmp.name)/'edge.sqlite');self.edge=EdgeStore(self.database)
        self.sample=PlugAdapter.telemetry(PLUG,plug_raw(),NOW);self.edge.accept_event(self.sample)
    def tearDown(self):self.edge.close();self.tmp.cleanup()
    def state(self):return self.edge.db.execute('SELECT attempts,delivered,blocked FROM forwarding').fetchone()
    def receipt(self):return {'data':{**{k:self.sample[k] for k in ['event_id','device_id','boot_id','sequence']},'durable':True}}
    def test_atomic_outbox_and_duplicate(self):
        self.edge.accept_event({**self.sample,'received_at':iso(NOW+1)})
        self.assertEqual(self.edge.status()['outbox_pending'],1)
        f=Forwarder(self.database,'https://platform.example','synthetic-test-token',sender=lambda kind,payload:self.receipt())
        self.assertTrue(f.once(1));self.assertEqual(self.state(),(0,1,0));self.assertFalse(f.once(2))
    def test_restart_retry_and_wrong_receipt(self):
        f=Forwarder(self.database,'https://platform.example','synthetic-test-token',sender=lambda *_:{'data':{'durable':True,'device_id':'wrong'}})
        f.once(1);self.assertEqual(self.state(),(1,0,0))
        f=Forwarder(self.database,'https://platform.example','synthetic-test-token',sender=lambda *_:self.receipt())
        f.once(2);self.assertEqual(self.state(),(1,1,0))
    def test_network_failure_and_conflict_retained(self):
        def fail(*_):raise OSError('offline')
        f=Forwarder(self.database,'https://platform.example','synthetic-test-token',sender=fail);f.once(1)
        self.assertEqual(self.state(),(1,0,0))
        def conflict(*_):raise urllib.error.HTTPError('https://platform.example',409,'conflict',{},None)
        f.sender=conflict;f.once(2);self.assertEqual(self.state(),(2,0,1));self.assertFalse(f.once(500))
        self.assertEqual(self.edge.db.execute('SELECT count(*) FROM iot_events').fetchone()[0],1)
    def test_origin_security(self):
        for origin,token in [('http://remote.example','test'),('https://user@platform.example','test'),('https://platform.example/path','test'),('https://platform.example','')]:
            with self.assertRaises(ValueError):Forwarder(self.database,origin,token)
    def test_nonmatching_tuple_never_acknowledges_delivery(self):
        receipt=self.receipt();receipt['data']['sequence']='999'
        f=Forwarder(self.database,'https://platform.example','synthetic-test-token',sender=lambda *_:receipt)
        f.once(1);self.assertEqual(self.state(),(1,0,0))

    def test_corrupt_stored_row_is_quarantined_without_killing_forwarder(self):
        with self.edge.db:self.edge.db.execute("UPDATE forwarding SET payload='{invalid-json'")
        forwarder=Forwarder(self.database,'https://platform.example','synthetic-test-token',sender=lambda *_:self.fail('bad payload not sent'))
        self.assertTrue(forwarder.once(1));self.assertEqual(self.state(),(0,0,1))
        self.assertFalse(forwarder.once(2))
