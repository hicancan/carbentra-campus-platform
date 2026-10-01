"""Upgrade fixture uses the exact prior persisted schema before new tables exist."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from fixtures import *
from store import EdgeStore
from migrations import migrate_legacy_outbox
from platform_forwarder import Forwarder
from contract import canonical

class LegacyMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=str(Path(self.temp.name)/'old-edge.sqlite');self.raw=plug_raw()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
            db.execute('CREATE TABLE telemetry(device TEXT,epoch TEXT,seq TEXT,received REAL,payload TEXT,PRIMARY KEY(device,epoch,seq))')
            db.execute('CREATE TABLE acknowledgements(device TEXT,command_id TEXT,received REAL,payload TEXT)')
            db.execute('CREATE TABLE forwarding(event_key TEXT PRIMARY KEY,kind TEXT NOT NULL,device TEXT NOT NULL,payload TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,next_attempt REAL NOT NULL DEFAULT 0,delivered INTEGER NOT NULL DEFAULT 0,blocked INTEGER NOT NULL DEFAULT 0,last_error TEXT)')
            db.execute('INSERT INTO telemetry VALUES(?,?,?,?,?)',(PLUG.device_id,self.raw['boot_epoch'],'1',NOW-86400,canonical(self.raw)))
            db.execute('INSERT INTO forwarding VALUES(?,?,?,?,?,?,?,?,?)',('old-key','telemetry',PLUG.device_id,canonical(self.raw),3,NOW-10,0,0,'OSError'))
        self.store=EdgeStore(self.path)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def test_versioned_conversion_preserves_exact_raw_identity_time_retry_and_receipt(self):
        result=migrate_legacy_outbox(self.store,[PLUG]);self.assertEqual(result['converted_pending'],1)
        kind,payload,attempts,retry=self.store.db.execute('SELECT kind,payload,attempts,next_attempt FROM forwarding').fetchone()
        value=json.loads(payload);self.assertEqual(kind,'event');self.assertEqual(value['raw'],self.raw)
        self.assertEqual(value['received_at'],iso(NOW-86400));self.assertEqual(value['boot_id'],self.raw['boot_epoch'])
        self.assertEqual((attempts,retry),(3,NOW-10))
        self.assertEqual(self.store.db.execute('SELECT received FROM telemetry').fetchone()[0],NOW-86400)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM legacy_outbox_archive').fetchone()[0],1)
        self.assertTrue(migrate_legacy_outbox(self.store,[PLUG])['already_applied'])
        seen=[]
        forward=Forwarder(self.path,'https://platform.example','fixture-token',sender=lambda kind,payload:seen.append(kind) or {'data':{'durable':True,**{k:value[k] for k in ('event_id','device_id','boot_id','sequence')}}})
        forward.once(NOW);self.assertEqual(seen,['event']);self.assertEqual(self.store.status()['outbox_delivered'],1)
    def test_missing_enrollment_quarantined_then_explicit_retry_preserves_time(self):
        self.assertEqual(migrate_legacy_outbox(self.store,[])['quarantined'],1)
        self.assertEqual(self.store.db.execute('SELECT blocked FROM forwarding').fetchone()[0],1)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM iot_events').fetchone()[0],0)
        self.assertEqual(migrate_legacy_outbox(self.store,[PLUG],True)['converted_pending'],1)
        self.assertEqual(json.loads(self.store.db.execute('SELECT payload FROM iot_events').fetchone()[0])['received_at'],iso(NOW-86400))
    def test_missing_original_time_cannot_be_retimed_to_migration_now(self):
        with self.store.db:self.store.db.execute('DELETE FROM telemetry')
        self.assertEqual(migrate_legacy_outbox(self.store,[PLUG])['quarantined'],1)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM iot_events').fetchone()[0],0)
        self.assertEqual(self.store.db.execute('SELECT reason FROM migration_quarantine').fetchone()[0],'original_telemetry_receipt_missing')
    def test_existing_conflict_stays_blocked_and_delivered_history_is_archived(self):
        with self.store.db:self.store.db.execute("UPDATE forwarding SET blocked=1,last_error='HTTPError'")
        self.assertEqual(migrate_legacy_outbox(self.store,[PLUG])['preserved_blocked'],1)
        self.assertEqual(self.store.db.execute('SELECT blocked,last_error FROM forwarding').fetchone(),(1,'HTTPError'))
    def test_conflicting_old_durable_identity_still_rejected_before_new_receipt(self):
        changed={**self.raw,'desired_on':False}
        with self.assertRaises(ValueError):self.store.accept_event(PlugAdapter.telemetry(PLUG,changed,NOW))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM iot_events').fetchone()[0],0)

    def test_already_delivered_rows_keep_original_receipt_in_archive_not_retransmission(self):
        with self.store.db:self.store.db.execute('UPDATE forwarding SET delivered=1')
        result=migrate_legacy_outbox(self.store,[PLUG]);self.assertEqual(result['archived_delivered'],1)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM forwarding').fetchone()[0],0)
        archived=json.loads(self.store.db.execute('SELECT original_row FROM legacy_outbox_archive').fetchone()[0])
        self.assertEqual(archived['delivered'],1);self.assertEqual(archived['payload'],canonical(self.raw))
        self.assertEqual(self.store.db.execute('SELECT received FROM telemetry').fetchone()[0],NOW-86400)

    def test_retired_legacy_writer_cannot_repopulate_old_application_outbox(self):
        migrate_legacy_outbox(self.store,[PLUG])
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.db:self.store.enqueue('telemetry',PLUG.device_id,canonical(self.raw),'late-old-writer')

    def test_retransmitted_delivered_legacy_sample_does_not_become_fresh(self):
        with self.store.db:self.store.db.execute('UPDATE forwarding SET delivered=1')
        migrate_legacy_outbox(self.store,[PLUG])
        self.store.accept_event(PlugAdapter.telemetry(PLUG,self.raw,NOW))
        snapshot=self.store.snapshot(PLUG.device_id,NOW)
        self.assertEqual(snapshot['event']['received_at'],iso(NOW-86400))
        self.assertFalse(snapshot['fresh'])
