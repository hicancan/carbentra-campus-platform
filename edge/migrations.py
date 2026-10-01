"""One-time v1 SQLite outbox migration; no permanent old application HTTP path.

Run before transports start and while the prior gateway is stopped. Original raw
telemetry/receipt rows remain untouched. Conversion uses explicit enrollment,
manufacturer validation and original receipt time, never migration wall time.
Unresolvable evidence is quarantined, not guessed, discarded or re-timestamped.
"""
from __future__ import annotations
import hashlib
import json
import math
import time
from adapters import PlugAdapter
from contract import canonical
from service import strict_json

VERSION='20261001_legacy_outbox_to_iot_v1'


def migrate_legacy_outbox(store, enrollments, retry_quarantine=False):
    enrolled={e.device_id:e for e in enrollments}
    db=store.db
    db.executescript('''
        CREATE TABLE IF NOT EXISTS edge_schema_migrations(version TEXT PRIMARY KEY, applied REAL NOT NULL, summary TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS legacy_outbox_archive(event_key TEXT PRIMARY KEY, original_row TEXT NOT NULL,
            canonical_event_id TEXT, disposition TEXT NOT NULL, migrated_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS migration_quarantine(event_key TEXT PRIMARY KEY, original_row TEXT NOT NULL,
            reason TEXT NOT NULL, quarantined_at REAL NOT NULL, resolved INTEGER NOT NULL DEFAULT 0);
    ''')
    db.commit()
    old=db.execute('SELECT summary FROM edge_schema_migrations WHERE version=?',(VERSION,)).fetchone()
    if old and not retry_quarantine:
        unexpected=db.execute("SELECT count(*) FROM forwarding WHERE kind='telemetry' AND blocked=0").fetchone()[0]
        if unexpected:
            raise ValueError('legacy writer produced outbox rows after migration; stop old service and review')
        return {**json.loads(old[0]),'already_applied':True}
    stats={'version':VERSION,'converted_pending':0,'archived_delivered':0,'quarantined':0,'preserved_blocked':0}
    columns=['event_key','kind','device','payload','attempts','next_attempt','delivered','blocked','last_error']
    migration_time=time.time()  # Audit timestamp only, never an observation/receipt timestamp.
    db.execute('BEGIN IMMEDIATE')
    try:
        rows=db.execute("SELECT "+','.join(columns)+" FROM forwarding WHERE kind='telemetry' ORDER BY rowid").fetchall()
        for values in rows:
            row=dict(zip(columns,values));key=row['event_key'];original=canonical(row)
            saved=db.execute('SELECT original_row FROM migration_quarantine WHERE event_key=?',(key,)).fetchone()
            if saved:
                original=saved[0];row=json.loads(original)  # Restore original delivery/error metadata on explicit retry.
            if row['delivered']:
                db.execute('INSERT OR IGNORE INTO legacy_outbox_archive VALUES(?,?,?,?,?)',(key,original,None,'already_delivered_legacy_receipt_preserved',migration_time))
                db.execute('DELETE FROM forwarding WHERE event_key=?',(key,));stats['archived_delivered']+=1
                continue
            try:
                raw=strict_json(row['payload'])
                if not isinstance(raw,dict):raise ValueError('legacy_payload_not_object')
                if type(row['attempts']) is not int or row['attempts']<0 or row['blocked'] not in (0,1) or type(row['next_attempt']) not in (int,float) or not math.isfinite(row['next_attempt']):
                    raise ValueError('legacy_retry_metadata_invalid')
                e=enrolled.get(row['device'])
                if e is None or e.product_family!='PLUG':raise ValueError('explicit_legacy_plug_enrollment_missing')
                if not store.legacy_telemetry:raise ValueError('original_telemetry_receipt_table_missing')
                if raw.get('device_id')!=row['device']:raise ValueError('legacy_outbox_device_mismatch')
                legacy=db.execute('SELECT received,payload FROM telemetry WHERE device=? AND epoch=? AND seq=?',(row['device'],raw.get('boot_epoch'),raw.get('sample_seq'))).fetchone()
                if legacy is None:raise ValueError('original_telemetry_receipt_missing')
                received,saved_payload=legacy
                if type(received) not in (int,float) or not math.isfinite(received):raise ValueError('original_received_time_invalid')
                if canonical(strict_json(saved_payload))!=canonical(raw):raise ValueError('legacy_durable_payload_conflict')
                event=PlugAdapter.telemetry(e,raw,received)
                payload=canonical(event)
                intrinsic={k:v for k,v in event.items() if k!='received_at'}
                fingerprint=hashlib.sha256(canonical(intrinsic).encode()).hexdigest()
                prior=db.execute('SELECT payload FROM iot_events WHERE device=? AND boot=? AND sequence=?',(event['device_id'],event['boot_id'],event['sequence'])).fetchone()
                if prior and prior[0]!=payload:raise ValueError('canonical_identity_or_original_receipt_conflict')
                prior_outbox=db.execute('SELECT kind,device,payload FROM forwarding WHERE event_key=?',(event['event_id'],)).fetchone()
                if prior_outbox and prior_outbox!=('event',event['device_id'],payload):raise ValueError('canonical_outbox_identity_conflict')
                db.execute('INSERT OR IGNORE INTO iot_events VALUES(?,?,?,?,?,?,?)',(event['event_id'],event['device_id'],event['boot_id'],event['sequence'],received,fingerprint,payload))
                db.execute('INSERT OR IGNORE INTO forwarding(event_key,kind,device,payload,attempts,next_attempt,delivered,blocked,last_error) VALUES(?,?,?,?,?,?,0,?,?)',
                    (event['event_id'],'event',event['device_id'],payload,row['attempts'],row['next_attempt'],row['blocked'],row['last_error']))
                if row['blocked']:
                    db.execute('UPDATE forwarding SET blocked=1,last_error=COALESCE(?,last_error) WHERE event_key=?',(row['last_error'],event['event_id']))
                db.execute('INSERT OR IGNORE INTO legacy_outbox_archive VALUES(?,?,?,?,?)',(key,original,event['event_id'],'converted_preserving_original_receipt',migration_time))
                db.execute('DELETE FROM forwarding WHERE event_key=?',(key,))
                db.execute('UPDATE migration_quarantine SET resolved=1 WHERE event_key=?',(key,))
                stats['converted_pending']+=1;stats['preserved_blocked']+=int(bool(row['blocked']))
            except (ValueError,TypeError,KeyError,OverflowError) as error:
                # Exact original row (including flags/retry time) is retained separately.
                reason=str(error)
                db.execute('INSERT OR IGNORE INTO migration_quarantine VALUES(?,?,?,?,0)',(key,original,reason,migration_time))
                db.execute("UPDATE forwarding SET blocked=1,last_error='migration_quarantined' WHERE event_key=?",(key,))
                stats['quarantined']+=1
        db.execute("""CREATE TRIGGER IF NOT EXISTS reject_retired_legacy_outbox_writer BEFORE INSERT ON forwarding
            WHEN NEW.kind='telemetry' BEGIN SELECT RAISE(ABORT,'legacy application outbox writer is retired'); END""")
        db.execute('INSERT INTO edge_schema_migrations VALUES(?,?,?) ON CONFLICT(version) DO UPDATE SET applied=excluded.applied,summary=excluded.summary',(VERSION,migration_time,canonical(stats)))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return stats
