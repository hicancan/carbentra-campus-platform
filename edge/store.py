"""Single durable ingress/outbox and offline snapshot store (WAL, FULL fsync).

Receipts mean committed edge durability only. Payload conflicts are rejected;
arrival time is not sample identity. Repeated BLE/MQTT samples do not refresh age.
"""
from __future__ import annotations
import hashlib
import math
from datetime import datetime, timezone
import json
import sqlite3
import time
from contract import canonical, timestamp, validate_event
from freshness import MONOTONIC_RATE_FLOOR, observation_freshness


class EdgeStore:
    def __init__(self, database):
        self.database = str(database)
        self.db = sqlite3.connect(self.database, timeout=5)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS iot_events(
            event_id TEXT PRIMARY KEY, device TEXT NOT NULL, boot TEXT NOT NULL,
            sequence TEXT NOT NULL, received REAL NOT NULL, fingerprint TEXT NOT NULL,
            payload TEXT NOT NULL, UNIQUE(device,boot,sequence));
        CREATE TABLE IF NOT EXISTS forwarding(
            event_key TEXT PRIMARY KEY, kind TEXT NOT NULL, device TEXT NOT NULL, payload TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0,
            delivered INTEGER NOT NULL DEFAULT 0, blocked INTEGER NOT NULL DEFAULT 0, last_error TEXT);
        CREATE TABLE IF NOT EXISTS wire_acks(
            event_key TEXT PRIMARY KEY, kind TEXT NOT NULL, device TEXT NOT NULL,
            received REAL NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS edge_manual_holds(
            device TEXT NOT NULL, channel TEXT NOT NULL, boot TEXT NOT NULL, created REAL NOT NULL, until REAL NOT NULL, command_id TEXT NOT NULL, PRIMARY KEY(device,channel));
        CREATE TABLE IF NOT EXISTS current_snapshots(
            device TEXT PRIMARY KEY, boot TEXT NOT NULL, sequence TEXT NOT NULL,
            event_id TEXT NOT NULL, received REAL NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS observation_clocks(
            device TEXT NOT NULL, boot TEXT NOT NULL, origin_upper REAL NOT NULL,
            monotonic_highwater INTEGER NOT NULL, utc_low_highwater REAL,
            received_highwater REAL, PRIMARY KEY(device,boot));
        CREATE TABLE IF NOT EXISTS known_boots(
            device TEXT NOT NULL, boot TEXT NOT NULL, retired INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(device,boot));
        CREATE TABLE IF NOT EXISTS auth_boots(
            device TEXT NOT NULL, boot TEXT NOT NULL, retired INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(device,boot));
        CREATE TABLE IF NOT EXISTS auth_highwater(
            device TEXT PRIMARY KEY, boot TEXT NOT NULL, sequence TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ingress_health(
            key TEXT PRIMARY KEY, value TEXT NOT NULL, updated REAL NOT NULL);
        ''')
        # Extend older stores without resetting any established clock bound. The
        # write transaction serializes concurrent opens during this additive upgrade.
        self.db.execute('BEGIN IMMEDIATE')
        if 'received_highwater' not in {row[1] for row in self.db.execute('PRAGMA table_info(observation_clocks)')}:
            self.db.execute('ALTER TABLE observation_clocks ADD COLUMN received_highwater REAL')
        self.db.commit()
        self.legacy_telemetry = self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='telemetry'").fetchone() is not None

    def close(self):
        self.db.close()

    def enqueue(self, kind, device, payload, key=None):
        key = key or hashlib.sha256((kind + '\n' + device + '\n' + payload).encode()).hexdigest()
        self.db.execute('INSERT OR IGNORE INTO forwarding(event_key,kind,device,payload) VALUES(?,?,?,?)', (key, kind, device, payload))
        return key

    def accept_event(self, value, authenticated=False):
        validate_event(value)
        device, boot, sequence = value['device_id'], value['boot_id'], value['sequence']
        self.db.execute('BEGIN IMMEDIATE')
        try:
            if self.legacy_telemetry and value['source_protocol']=='plug-wire-v2':
                legacy=self.db.execute('SELECT received,payload FROM telemetry WHERE device=? AND epoch=? AND seq=?',(device,boot,sequence)).fetchone()
                if legacy:
                    if canonical(json.loads(legacy[1])) != canonical(value['raw']):
                        raise ValueError('conflicting duplicate legacy sample')
                    if type(legacy[0]) not in (int,float) or not math.isfinite(legacy[0]):
                        raise ValueError('original legacy receipt time unavailable')
                    value={**value,'received_at':datetime.fromtimestamp(legacy[0],timezone.utc).isoformat().replace('+00:00','Z')}
            payload = canonical(value)
            # Preserve first receipt, including an old durable receipt after upgrade.
            intrinsic = {k:v for k,v in value.items() if k != 'received_at'}
            fingerprint = hashlib.sha256(canonical(intrinsic).encode()).hexdigest()
            received = timestamp(value['received_at']).timestamp()
            if authenticated:
                previous_auth = self.db.execute('SELECT boot,sequence FROM auth_highwater WHERE device=?', (device,)).fetchone()
                retired_auth = self.db.execute('SELECT retired FROM auth_boots WHERE device=? AND boot=?', (device,boot)).fetchone()
                if (retired_auth and retired_auth[0]) or (previous_auth and previous_auth[0] == boot and int(sequence) <= int(previous_auth[1])):
                    raise ValueError('authenticated sample replay')
                if previous_auth and previous_auth[0] != boot:
                    self.db.execute('UPDATE auth_boots SET retired=1 WHERE device=? AND boot=?', (device,previous_auth[0]))
                self.db.execute('INSERT OR IGNORE INTO auth_boots(device,boot) VALUES(?,?)', (device,boot))
                self.db.execute('INSERT INTO auth_highwater VALUES(?,?,?) ON CONFLICT(device) DO UPDATE SET boot=excluded.boot,sequence=excluded.sequence', (device,boot,sequence))
            existing = self.db.execute('SELECT event_id,fingerprint,payload FROM iot_events WHERE device=? AND boot=? AND sequence=?', (device, boot, sequence)).fetchone()
            if existing:
                if existing[:2] != (value['event_id'], fingerprint):
                    raise ValueError('conflicting duplicate sample')
                self.db.commit()
                return {'durable': True, 'duplicate': True, 'event_id': existing[0], 'device_id': device, 'boot_id': boot, 'sequence': sequence}
            self.db.execute('INSERT INTO iot_events VALUES(?,?,?,?,?,?,?)', (value['event_id'], device, boot, sequence, received, fingerprint, payload))
            self.enqueue('event', device, payload, value['event_id'])
            current = self.db.execute('SELECT boot,sequence,payload FROM current_snapshots WHERE device=?', (device,)).fetchone()
            # Seed from the original cached receipt when upgrading an existing
            # database; neither upgrades nor restarts renew a boot's age bound.
            if current:
                self._record_observation_clock(json.loads(current[2]))
            self._record_observation_clock(value)
            retired = self.db.execute('SELECT retired FROM known_boots WHERE device=? AND boot=?', (device, boot)).fetchone()
            self.db.execute('INSERT OR IGNORE INTO known_boots(device,boot) VALUES(?,?)', (device, boot))
            authenticated_current = current and json.loads(current[2])['source_protocol'] == 'presence-gatt-v1'
            promote = authenticated or not authenticated_current
            if promote and (authenticated or not (retired and retired[0])) and (not current or current[0] != boot or int(sequence) > int(current[1]) or (authenticated and not authenticated_current)):
                if current and current[0] != boot:
                    self.db.execute('UPDATE known_boots SET retired=1 WHERE device=? AND boot=?', (device, current[0]))
                self.db.execute('INSERT INTO current_snapshots VALUES(?,?,?,?,?,?) ON CONFLICT(device) DO UPDATE SET boot=excluded.boot,sequence=excluded.sequence,event_id=excluded.event_id,received=excluded.received,payload=excluded.payload', (device, boot, sequence, value['event_id'], received, payload))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return {'durable': True, 'duplicate': False, 'event_id': value['event_id'], 'device_id': device, 'boot_id': boot, 'sequence': sequence}

    def accept_ack(self, kind, device, value, now=None):
        if kind not in {'ack', 'switch_ack'}:
            raise ValueError('unsupported ACK adapter')
        payload = canonical(value)
        key = hashlib.sha256((kind + '\n' + device + '\n' + payload).encode()).hexdigest()
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO wire_acks VALUES(?,?,?,?,?)', (key, kind, device, time.time() if now is None else now, payload))
            self.enqueue(kind, device, payload, key)
        return key

    def snapshot(self, device, now=None, maximum_age=10):
        row = self.db.execute('SELECT received,payload FROM current_snapshots WHERE device=?', (device,)).fetchone()
        if not row:
            return None
        now = time.time() if now is None else now
        if (type(now) not in (int, float) or not math.isfinite(now)
                or type(maximum_age) not in (int, float) or not math.isfinite(maximum_age) or maximum_age <= 0):
            raise ValueError('finite time and positive maximum age required')
        value = json.loads(row[1])
        bound = self.db.execute('SELECT origin_upper,monotonic_highwater,utc_low_highwater,received_highwater FROM observation_clocks WHERE device=? AND boot=?',
                                (device, value['boot_id'])).fetchone()
        return {'event': value, **observation_freshness(value, now, maximum_age, bound)}

    def _record_observation_clock(self, value):
        mono = value['monotonic_ms']
        if value['product_family'] not in {'PLUG', 'SWITCH'} or mono is None:
            return
        received = timestamp(value['received_at']).timestamp()
        bound = self.db.execute('SELECT origin_upper,monotonic_highwater,utc_low_highwater,received_highwater FROM observation_clocks WHERE device=? AND boot=?',
                                (value['device_id'], value['boot_id'])).fetchone()
        # Clock coherence is checked against the previous trusted bound before any
        # durable update, including when seeding from a cached pre-upgrade event.
        # No age cutoff here: valid delayed observations still tighten history, but
        # future/inconsistent/reversed/untrusted clocks must not poison later data.
        if not observation_freshness(value, received, math.inf, bound)['fresh']:
            return
        # An old packet or a forward jump of the gateway clock cannot establish
        # trusted receipt time. Retain coherent device bounds, but do not make a
        # corrected gateway wait for the erroneous future highwater to catch up.
        trusted_received = received if observation_freshness(value, received, 10, bound)['fresh'] else None
        origin = received - mono / 1000 / MONOTONIC_RATE_FLOOR
        low = value['raw'].get('unix_lower_s') if value['time_quality'] == 'authenticated' else None
        if type(low) not in (int, float):
            low = None
        self.db.execute('''INSERT INTO observation_clocks VALUES(?,?,?,?,?,?)
            ON CONFLICT(device,boot) DO UPDATE SET
            origin_upper=min(origin_upper,excluded.origin_upper),
            monotonic_highwater=max(monotonic_highwater,excluded.monotonic_highwater),
            utc_low_highwater=CASE WHEN utc_low_highwater IS NULL THEN excluded.utc_low_highwater
                WHEN excluded.utc_low_highwater IS NULL THEN utc_low_highwater
                ELSE max(utc_low_highwater,excluded.utc_low_highwater) END,
            received_highwater=CASE WHEN received_highwater IS NULL THEN excluded.received_highwater
                WHEN excluded.received_highwater IS NULL THEN received_highwater
                ELSE max(received_highwater,excluded.received_highwater) END''',
            (value['device_id'], value['boot_id'], origin, mono, low, trusted_received))

    def active_manual_hold(self, device, channel, now=None):
        now=time.time() if now is None else now
        row=self.db.execute('SELECT created,until,command_id FROM edge_manual_holds WHERE device=? AND channel=?',(device,channel)).fetchone()
        return {'active':bool(row and (now<row[0] or now<row[1])), 'until':row[1] if row else None, 'command_id':row[2] if row else None}

    def health(self, key, value, now=None):
        with self.db:
            self.db.execute('INSERT INTO ingress_health VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated=excluded.updated', (key, canonical(value), time.time() if now is None else now))

    def status(self):
        rows = self.db.execute('SELECT delivered,blocked,count(*) FROM forwarding GROUP BY delivered,blocked').fetchall()
        return {'outbox_pending': sum(n for delivered, blocked, n in rows if not delivered and not blocked),
                'outbox_blocked': sum(n for delivered, blocked, n in rows if not delivered and blocked),
                'outbox_delivered': sum(n for delivered, blocked, n in rows if delivered),
                'devices_cached': self.db.execute('SELECT count(*) FROM current_snapshots').fetchone()[0]}
