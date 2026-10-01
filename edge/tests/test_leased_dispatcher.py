from contextlib import closing
import time
import copy
import tempfile
from pathlib import Path
import unittest
from fixtures import *
from store import EdgeStore
from channel_transport import ChannelTransport
from leased_dispatcher import LeasedDispatcher

class LeasedDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=str(Path(self.tmp.name)/'edge.sqlite');self.store=EdgeStore(self.db)
        self.store.accept_event(SwitchAdapter.telemetry(SWITCH,switch_raw(),NOW))
        self.sent=[];self.reports=[]
        channels=ChannelTransport(self.db,[SWITCH],lambda *args:self.sent.append(args) or True,enable_virtual=True)
        parent=self
        class Plug:
            def report(self,*args):parent.reports.append(args)
        self.dispatcher=LeasedDispatcher(None,Plug(),channels,lambda:True)
        cmd=command();self.item={'id':cmd['id'],'device_id':cmd['device_id'],'source_mode':'SIMULATED','dispatch_mode':'VIRTUAL','transport':'MQTT','lease_id':cmd['authority']['lease_id'],'lease_expires_at':cmd['authority']['lease_expires_at'],'canonical_command':cmd}
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_canonical_switch_leases_and_retry_reports_do_not_republish(self):
        self.assertEqual(self.dispatcher.process(self.item,NOW)['status'],'published')
        changed=copy.deepcopy(self.item);changed['lease_id']='new-lease';changed['canonical_command']['authority']['lease_id']='new-lease'
        changed['lease_expires_at']=iso(NOW+25);changed['canonical_command']['authority']['lease_expires_at']=iso(NOW+25);changed['canonical_command']['expires_at']=iso(NOW+22)
        self.assertEqual(self.dispatcher.process(changed,NOW+1)['status'],'published')
        self.assertEqual(len(self.sent),1);self.assertEqual(len(self.reports),2)
    def test_no_family_channel_dispatch_or_lease_confusion(self):
        for field,value in [('device_id','other'),('source_mode','REAL'),('dispatch_mode','PHYSICAL'),('transport','HTTP'),('lease_id','wrong')]:
            item=copy.deepcopy(self.item);item[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.dispatcher.process(item,NOW)
        self.assertEqual(self.sent,[])

    def test_lost_receipt_retries_after_restart_without_server_releasing_or_republish(self):
        self.dispatcher.sender=lambda *_:(_ for _ in ()).throw(OSError('cloud disconnected'))
        self.assertEqual(self.dispatcher.process(self.item,NOW)['status'],'published')
        self.assertEqual(len(self.sent),1)
        with closing(__import__('sqlite3').connect(self.db)) as db, db:
            self.assertEqual(db.execute('SELECT delivered FROM delivery_outbox').fetchone()[0],0)
        restarted=LeasedDispatcher(None,self.dispatcher.plug,ChannelTransport(self.db,[SWITCH],lambda *_:self.fail('must not republish'),enable_virtual=True),lambda:False)
        restarted.reconcile(now=time.time()+10)
        self.assertEqual(len(self.sent),1)
        with closing(__import__('sqlite3').connect(self.db)) as db, db:
            self.assertEqual(db.execute('SELECT delivered FROM delivery_outbox').fetchone()[0],1)

    def test_crash_between_publish_inbox_and_receipt_enqueue_recovers_only_receipt(self):
        self.dispatcher._remember(self.item)
        result=self.dispatcher.channels.process(self.item['canonical_command'],NOW)
        self.assertEqual(result['status'],'published');self.assertEqual(len(self.sent),1)
        self.dispatcher.channels.publisher=lambda *_:self.fail('must not replay after restart')
        self.dispatcher.reconcile(now=NOW+1)
        self.assertEqual(len(self.sent),1);self.assertEqual(self.reports[0][2],'published')

    def test_crash_after_sending_commit_before_publish_remains_uncertain(self):
        import sqlite3
        from contract import canonical
        self.dispatcher._remember(self.item)
        cmd=self.item['canonical_command']
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute('INSERT INTO command_inbox VALUES(?,?,?,?,?,?,?)',(cmd['id'],cmd['device_id'],cmd['sequence'],canonical({k:v for k,v in cmd.items() if k not in {'authority','expires_at'}}),'sending',None,NOW))
        self.dispatcher.channels.publisher=lambda *_:self.fail('crash ambiguity must never replay')
        self.dispatcher.reconcile(now=NOW+1)
        self.assertEqual(self.sent,[])
        self.assertEqual(self.reports[0][2:4],('failed','mqtt_delivery_uncertain'))

    def test_power_loss_after_publish_before_outcome_commit_never_republishes(self):
        def power_loss(topic,payload):
            self.sent.append((topic,payload))
            raise SystemExit('synthetic power loss after MQTT call')
        self.dispatcher.channels.publisher=power_loss
        with self.assertRaises(SystemExit):self.dispatcher.process(self.item,NOW)
        self.assertEqual(len(self.sent),1)
        restarted=LeasedDispatcher(None,self.dispatcher.plug,ChannelTransport(self.db,[SWITCH],lambda *_:self.fail('must not replay'),enable_virtual=True),lambda:True)
        restarted.reconcile(now=NOW+1)
        self.assertEqual(len(self.sent),1);self.assertEqual(self.reports[0][2:4],('failed','mqtt_delivery_uncertain'))

    def test_never_started_expired_lease_is_not_a_new_command(self):
        self.dispatcher._remember(self.item)
        self.dispatcher.channels.publisher=lambda *_:self.fail('expired unstarted lease')
        self.dispatcher.reconcile(now=NOW+31)
        self.assertEqual(self.sent,[]);self.assertEqual(self.reports[0][2],'expired')

    def test_malformed_lease_does_not_poison_durable_recovery(self):
        item=copy.deepcopy(self.item);del item['lease_expires_at']
        with self.assertRaises(ValueError):self.dispatcher.process(item,NOW)
        import sqlite3
        with closing(sqlite3.connect(self.db)) as db, db:self.assertEqual(db.execute('SELECT count(*) FROM leased_requests').fetchone()[0],0)
