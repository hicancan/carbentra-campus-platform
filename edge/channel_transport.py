"""Typed channel command translator and durable, never-blind-replay dispatcher.

Real dispatch needs an exact process opt-in, matching per-device release, fresh
same-boot evidence, declared write channel and lease. The device still enforces
its own commissioning, protection and manual priority. A PUBACK is not execution.
"""
from __future__ import annotations
from contextlib import closing
import json
import sqlite3
import time
from adapters import descriptor
from contract import canonical, timestamp, validate_command
from store import EdgeStore


def get_reading(event, channel, capability):
    return next((r for r in event['readings'] if r['channel_id'] == channel and r['capability'] == capability), None)


class ChannelTransport:
    def __init__(self, database, enrollments, publisher, enable_virtual=False,
                 physical_enabled=False, physical_releases=None):
        if type(enable_virtual) is not bool or type(physical_enabled) is not bool:
            raise ValueError('dispatch flags must be exact booleans')
        self.database = str(database)
        self.enrolled = {e.device_id: e for e in enrollments}
        self.publisher = publisher
        self.enable_virtual = enable_virtual
        self.physical_enabled = physical_enabled
        self.releases = physical_releases or {}
        if not isinstance(self.releases, dict) or not set(self.releases) <= set(self.enrolled):
            raise ValueError('unknown physical release device')
        if any(self.enrolled[d].source_mode != 'REAL' or not isinstance(v, str) or not v for d, v in self.releases.items()):
            raise ValueError('physical releases must identify real enrolled devices')
        if physical_enabled and not self.releases:
            raise ValueError('physical dispatch requires per-device release records')
        with closing(sqlite3.connect(database)) as db, db:
            db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
            db.execute('''CREATE TABLE IF NOT EXISTS command_inbox(
                id TEXT PRIMARY KEY, device TEXT NOT NULL, seq TEXT NOT NULL, wire TEXT NOT NULL,
                state TEXT NOT NULL, reason TEXT, updated REAL NOT NULL)''')
            db.execute('''CREATE TABLE IF NOT EXISTS channel_command_audit(
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL,
                reason TEXT, updated REAL NOT NULL)''')

    def translate(self, command, snapshot, now):
        e = self.enrolled[command['device_id']]
        if e.product_family != command['product_family']:
            raise ValueError('family_mismatch')
        if snapshot is None or not snapshot['fresh']:
            raise ValueError('fresh_observation_required')
        if snapshot.get('edge_hold', {}).get('active') and 'manual_hold_seconds' not in command:
            raise ValueError('backend_edge_manual_hold')
        state = snapshot['event']
        if state['boot_id'] != command['boot_id'] or state['source_mode'] != command['source_mode']:
            raise ValueError('boot_or_source_changed')
        caps = next((c['capabilities'] for c in descriptor(e)['channels'] if c['channel_id'] == command['channel_id']), [])
        if not any(c['capability'] == command['capability'] and c['available'] and c['access'] in {'write', 'read_write'} for c in caps):
            raise ValueError('capability_not_declared')
        health = get_reading(state, 'device', 'device.health')
        if not health or health['quality'] != 'valid' or health['value'] != 'ok':
            raise ValueError('fault_or_maintenance_or_unknown')
        if command['source_mode'] == 'REAL' and health.get('details',{}).get('actuation_enabled') is not True:
            raise ValueError('device_actuation_not_enabled')
        mode = get_reading(state, command['channel_id'], 'control.mode')
        if not mode or mode['quality'] != 'valid' or mode['value'] != 'auto':
            raise ValueError('manual_or_protected_or_unknown')
        hold = get_reading(state, command['channel_id'], 'control.manual_hold_until')
        if not hold or hold['quality'] != 'valid' or state['monotonic_ms'] is None or hold['value'] > state['monotonic_ms']:
            raise ValueError('manual_hold_or_unknown')
        remaining = min(timestamp(command['expires_at']).timestamp(), timestamp(command['authority']['lease_expires_at']).timestamp()) - now
        if remaining <= 0:
            raise ValueError('command_or_lease_expired')
        if e.product_family == 'PLUG':
            if not e.profile_id:
                raise ValueError('plug_profile_not_enrolled')
            wire = {'id': command['id'], 'device_id': e.device_id, 'profile_id': e.profile_id,
                'seq': command['sequence'], 'issued_s': int(timestamp(command['issued_at']).timestamp()),
                'expires_s': int(min(timestamp(command['expires_at']).timestamp(), timestamp(command['authority']['lease_expires_at']).timestamp())),
                'action': 'restore' if command['value'] else 'shed'}
            if wire['expires_s'] <= now:
                raise ValueError('command_or_lease_expired')
            from command_transport import wire_command
            wire_command(wire, e.device_id)
            return f'carbentra/v1/{e.device_id}/cmd', wire
        if e.product_family == 'SWITCH':
            # Conservative deadline from last observed uptime. Do not extrapolate an
            # offline cached device clock; short latency only consumes the window.
            ttl_ms = min(30000, int(remaining * 1000))
            if ttl_ms <= int(snapshot['control_age_seconds'] * 1000):
                raise ValueError('insufficient_fresh_ttl')
            return f'carbentra/switch/{e.device_id}/command', {
                'id': command['id'], 'boot_id': command['boot_id'], 'seq': command['sequence'],
                'channel': int(command['channel_id'].split('.')[1]), 'on': command['value'],
                'expires_uptime_ms': str(state['monotonic_ms'] + ttl_ms)}
        raise ValueError('unsupported_actuator')

    def process(self, command, now=None):
        started = time.monotonic()
        now = time.time() if now is None else now
        validate_command(command)
        device, cid, seq = command['device_id'], command['id'], command['sequence']
        status, reason, topic, wire = None, None, None, None
        e = self.enrolled.get(device)
        if e is None:
            reason = 'not_enrolled'
        elif e.source_mode != command['source_mode']:
            reason = 'source_mismatch'
        elif e.source_mode == 'SIMULATED' and not self.enable_virtual:
            reason = 'virtual_dispatch_disabled'
        elif e.source_mode == 'REAL' and not (self.physical_enabled and device in self.releases and self.releases[device] == command['authority'].get('release_id')):
            reason = 'physical_release_not_allowlisted'
        elif now < timestamp(command['issued_at']).timestamp():
            reason = 'future_command'
        elif now >= min(timestamp(command['expires_at']).timestamp(), timestamp(command['authority']['lease_expires_at']).timestamp()):
            status, reason = 'expired', 'command_or_lease_expired'
        if not reason:
            store = EdgeStore(self.database)
            try:
                snapshot = store.snapshot(device, now)
                if snapshot is not None:
                    snapshot['edge_hold'] = store.active_manual_hold(device, command['channel_id'], now)
                topic, wire = self.translate(command, snapshot, now)
            except ValueError as error:
                reason = str(error)
            finally:
                store.close()
        # Canonical command, not mutable translated uptime, defines inbox identity.
        serialized = canonical({k:v for k,v in command.items() if k not in {'authority','expires_at'}})
        db = sqlite3.connect(self.database, timeout=5)
        db.execute('PRAGMA synchronous=FULL')
        try:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT device,seq,wire,state,reason FROM command_inbox WHERE id=?', (cid,)).fetchone()
            if existing:
                if existing[:3] != (device, seq, serialized):
                    status, reason = 'failed', 'conflicting_command_identity'
                else:
                    status = existing[3] if existing[3] in {'published', 'failed', 'expired'} else 'failed'
                    reason = existing[4] if existing[3] in {'published', 'failed', 'expired'} else 'mqtt_delivery_uncertain'
                db.commit()
                return {'id': cid, 'status': status, 'reason': reason}
            if not reason:
                previous = db.execute("SELECT seq FROM command_inbox WHERE device=? AND state IN ('sending','published','uncertain')", (device,)).fetchall()
                if any(int(row[0]) >= int(seq) for row in previous):
                    reason = 'replayed_sequence'
            status = status or ('failed' if reason else 'sending')
            if status == 'sending' and command.get('manual_hold_seconds'):
                db.execute('INSERT INTO edge_manual_holds VALUES(?,?,?,?,?,?) ON CONFLICT(device,channel) DO UPDATE SET boot=excluded.boot,created=excluded.created,until=excluded.until,command_id=excluded.command_id', (device,command['channel_id'],command['boot_id'],now,now+command['manual_hold_seconds'],cid))
            db.execute('INSERT INTO command_inbox VALUES(?,?,?,?,?,?,?)', (cid, device, seq, serialized, status, reason, now))
            db.execute('INSERT INTO channel_command_audit VALUES(?,?,?,?,?)', (cid, canonical(command), status, reason, now))
            db.commit()
            if status == 'sending':
                try:
                    remaining = min(timestamp(command['expires_at']).timestamp(), timestamp(command['authority']['lease_expires_at']).timestamp()) - now
                    if time.monotonic() - started >= remaining:
                        status, reason = 'expired', 'command_or_lease_expired_before_publish'
                        with db:
                            db.execute('UPDATE command_inbox SET state=?,reason=?,updated=? WHERE id=?', (status,reason,now,cid))
                            db.execute('UPDATE channel_command_audit SET status=?,reason=?,updated=? WHERE id=?', (status,reason,now,cid))
                        return {'id':cid,'status':status,'reason':reason}
                    published = self.publisher(topic, canonical(wire)) is True
                except Exception:
                    published = False
                status, reason = ('published', None) if published else ('failed', 'mqtt_delivery_uncertain')
                with db:
                    db.execute('UPDATE command_inbox SET state=?,reason=?,updated=? WHERE id=?', ('published' if published else 'uncertain', reason, now, cid))
                    db.execute('UPDATE channel_command_audit SET status=?,reason=?,updated=? WHERE id=?', (status, reason, now, cid))
            return {'id': cid, 'status': status, 'reason': reason}
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
