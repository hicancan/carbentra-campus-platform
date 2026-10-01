"""One backend lease stream and durable receipts, routed to concrete drivers.

Backend leases are deliberately never blindly reissued. Store the lease before
processing, then durably queue its delivery receipt. On restart an attempted send
is resolved from the driver's inbox; only its HTTP receipt is retried.
"""
from contextlib import closing
import json
import sqlite3
import time
import urllib.error
from contract import canonical, timestamp, validate_command


class LeasedDispatcher:
    def __init__(self, http, plug_transport, channel_transport, ready):
        self.http = http
        self.plug = plug_transport
        self.channels = channel_transport
        self.ready = ready
        self.database = channel_transport.database
        self.sender = plug_transport.report
        # The legacy concrete Plug driver delegates only reporting to this outbox.
        # It retains its independently tested delivery and physical release gates.
        self.plug.reporter = self._queue_delivery
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
            db.executescript('''
            CREATE TABLE IF NOT EXISTS leased_requests(
                id TEXT NOT NULL, lease_id TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(id,lease_id));
            CREATE TABLE IF NOT EXISTS delivery_outbox(
                id TEXT NOT NULL, lease_id TEXT NOT NULL, status TEXT NOT NULL, reason TEXT,
                attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0,
                delivered INTEGER NOT NULL DEFAULT 0, blocked INTEGER NOT NULL DEFAULT 0,
                last_error TEXT, PRIMARY KEY(id,lease_id));
            ''')

    def _remember(self, item):
        serialized = canonical(item)
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT payload FROM leased_requests WHERE id=? AND lease_id=?', (item['id'], item['lease_id'])).fetchone()
            if old and old[0] != serialized:
                raise ValueError('conflicting lease identity')
            db.execute('INSERT OR IGNORE INTO leased_requests VALUES(?,?,?)', (item['id'], item['lease_id'], serialized))

    def _send_receipt(self, identity, lease, status, reason, now=None):
        now = time.time() if now is None else now
        try:
            self.sender(identity, lease, status, reason)
            with closing(sqlite3.connect(self.database)) as db, db:
                db.execute('PRAGMA synchronous=FULL')
                db.execute('UPDATE delivery_outbox SET delivered=1,last_error=NULL WHERE id=? AND lease_id=?', (identity,lease))
            return True
        except (OSError, ValueError, TypeError) as error:
            blocked = isinstance(error, urllib.error.HTTPError) and error.code == 409
            with closing(sqlite3.connect(self.database)) as db, db:
                row=db.execute('SELECT attempts FROM delivery_outbox WHERE id=? AND lease_id=?',(identity,lease)).fetchone()
                attempts=row[0] if row else 0
                db.execute('UPDATE delivery_outbox SET attempts=attempts+1,next_attempt=?,blocked=?,last_error=? WHERE id=? AND lease_id=?',
                    (now+min(30,2**min(attempts,5)),int(blocked),type(error).__name__,identity,lease))
            return False

    def _queue_delivery(self, identity, lease, status, reason):
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT status,reason,delivered FROM delivery_outbox WHERE id=? AND lease_id=?',(identity,lease)).fetchone()
            if prior and prior[:2] != (status,reason):
                raise ValueError('conflicting durable delivery outcome')
            db.execute('INSERT OR IGNORE INTO delivery_outbox(id,lease_id,status,reason) VALUES(?,?,?,?)',(identity,lease,status,reason))
        if not prior or not prior[2]:
            self._send_receipt(identity,lease,status,reason)

    def process(self, item, now=None):
        if not isinstance(item, dict):
            raise ValueError('leased command must be an object')
        lease=item.get('lease_id');deadline=item.get('lease_expires_at')
        if not isinstance(lease,str) or not 1<=len(lease)<=128 or not isinstance(deadline,str):
            raise ValueError('invalid lease identity/deadline')
        timestamp(deadline)
        if 'canonical_command' not in item:
            from command_transport import wire_command
            wire_command(item.get('wire'),item.get('device_id'))
            if item.get('id')!=item['wire']['id'] or not isinstance(item.get('lease_id'),str):
                raise ValueError('invalid Plug lease identity')
            self._remember(item)
            return self.plug.process(item, now)
        command = validate_command(item['canonical_command'])
        if command['product_family'] != 'SWITCH':
            raise ValueError('typed lease currently supports concrete Switch only')
        if item.get('id') != command['id'] or item.get('device_id') != command['device_id'] or item.get('source_mode') != command['source_mode'] or item.get('transport') != 'MQTT':
            raise ValueError('canonical lease identity/source/transport mismatch')
        authority = command['authority']
        if authority['kind'] not in {'cloud','manual'} or item.get('lease_id') != authority['lease_id']:
            raise ValueError('cloud lease authority mismatch')
        if timestamp(item['lease_expires_at']) != timestamp(authority['lease_expires_at']):
            raise ValueError('cloud lease deadline mismatch')
        expected_mode = 'VIRTUAL' if command['source_mode'] == 'SIMULATED' else 'PHYSICAL'
        if item.get('dispatch_mode') != expected_mode:
            raise ValueError('cloud lease dispatch mode mismatch')
        if expected_mode == 'PHYSICAL' and item.get('release_id') != authority.get('release_id'):
            raise ValueError('physical release mismatch')
        self._remember(item)
        result = self.channels.process(command, now)
        self._queue_delivery(command['id'],item['lease_id'],result['status'],result['reason'])
        return result

    def reconcile(self, now=None):
        now=time.time() if now is None else now
        with closing(sqlite3.connect(self.database)) as db, db:
            pending=db.execute('''SELECT r.payload,i.state FROM leased_requests r
                LEFT JOIN command_inbox i ON i.id=r.id
                WHERE NOT EXISTS(SELECT 1 FROM delivery_outbox d WHERE d.id=r.id AND d.lease_id=r.lease_id)
                ORDER BY r.rowid LIMIT 20''').fetchall()
        for serialized,state in pending:
            # Existing sending/published/uncertain states cannot publish again.
            # A never-started item waits for broker availability (and expiry is
            # independently checked by its driver before any later first send).
            if state is not None or self.ready():
                self.process(json.loads(serialized),now)
        with closing(sqlite3.connect(self.database)) as db, db:
            receipts=db.execute('SELECT id,lease_id,status,reason FROM delivery_outbox WHERE delivered=0 AND blocked=0 AND next_attempt<=? ORDER BY rowid LIMIT 20',(now,)).fetchall()
        for identity,lease,status,reason in receipts:
            self._send_receipt(identity,lease,status,reason,now)
        return len(receipts)

    def once(self):
        self.reconcile()
        if not self.ready():
            return 0
        response = self.http.request('GET', '/api/v1/adapter/commands?limit=20')
        items = response.get('data') if isinstance(response, dict) else None
        if not isinstance(items, list) or len(items) > 20:
            raise ValueError('invalid command batch')
        # Firmware replay guard is device-global, even when channels differ.
        def order(item):
            body=item.get('canonical_command',item.get('wire',{}))
            return (str(item.get('device_id','')), int(body.get('sequence',body.get('seq','0'))))
        try:
            items=sorted(items,key=order)
        except (TypeError,KeyError,AttributeError) as error:
            raise ValueError('malformed leased command batch') from error
        count = 0
        for item in items:
            if not self.ready():
                break
            self.process(item)
            count += 1
        return count
