"""Small, explicit local rules with bounded operator leases and no inferred vacancy.

Priority: fault > maintenance/protected > manual hold > lease/expiry > fresh
qualified condition. Missing/stale evidence never means vacancy. Cached policy
survives outage; authority never expands on reconnect. Rules are evaluate-only
unless runtime dispatch was independently enabled. No dynamic code/eval is used.
"""
from __future__ import annotations
from contextlib import closing
import hashlib
import json
import re
import sqlite3
import time
from adapters import iso
from channel_transport import get_reading
from contract import canonical, timestamp, validate_command
from store import EdgeStore


class RuleEngine:
    def __init__(self, database):
        self.database = str(database)
        with closing(sqlite3.connect(database)) as db, db:
            db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
            db.executescript('''
            CREATE TABLE IF NOT EXISTS rule_bundle(id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS rule_state(id TEXT PRIMARY KEY, since REAL, last_received REAL, last_event TEXT, last_command_event TEXT);
            CREATE TABLE IF NOT EXISTS rule_leases(lease_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, next_sequence TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS rule_evaluations(id TEXT PRIMARY KEY, status TEXT NOT NULL, reason TEXT NOT NULL, updated REAL NOT NULL);
            ''')

    def install(self, bundle):
        if not isinstance(bundle, dict) or set(bundle) != {'schema_version', 'revision', 'valid_until', 'rules'} or type(bundle['schema_version']) is not int or bundle['schema_version'] != 1 or type(bundle['revision']) is not int or bundle['revision'] <= 0:
            raise ValueError('invalid local rule bundle')
        timestamp(bundle['valid_until'])
        if not isinstance(bundle['rules'], list) or len(bundle['rules']) > 64:
            raise ValueError('invalid rule count')
        ids = set(); ranges = {}
        for rule in bundle['rules']:
            required = {'id', 'sensor_device_id', 'target_device_id', 'channel_id', 'when_present', 'desired_on', 'stable_for_seconds', 'maximum_age_seconds'}
            if not isinstance(rule, dict) or not required <= set(rule) or set(rule) - required - {'lease', 'raw_light_below'}:
                raise ValueError('invalid rule fields')
            if not isinstance(rule['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',rule['id']) or rule['id'] in ids:
                raise ValueError('duplicate/invalid rule identity')
            ids.add(rule['id'])
            if any(not isinstance(rule[k],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,47}',rule[k]) for k in ('sensor_device_id','target_device_id')) or rule['channel_id'] not in {'relay.1','relay.2','relay.3'}:
                raise ValueError('invalid rule device/channel identity')
            if type(rule['when_present']) is not bool or type(rule['desired_on']) is not bool:
                raise ValueError('boolean rule condition/action required')
            if type(rule['maximum_age_seconds']) not in (int,float) or not 0 < rule['maximum_age_seconds'] <= 5:
                raise ValueError('bounded observation freshness required')
            if type(rule['stable_for_seconds']) not in (int,float) or not 0 <= rule['stable_for_seconds'] <= 3600:
                raise ValueError('invalid stability interval')
            if not rule['when_present'] and rule['stable_for_seconds'] < 60:
                raise ValueError('absence rule requires at least 60 seconds of fresh continuous evidence')
            if 'raw_light_below' in rule and (type(rule['raw_light_below']) is not int or not 0 <= rule['raw_light_below'] <= 65535):
                raise ValueError('raw light threshold must be an explicit ADC count')
            lease = rule.get('lease')
            if lease:
                fields = {'lease_id', 'issuer', 'issued_at', 'expires_at', 'offline_until', 'sequence_start', 'sequence_end'}
                if not isinstance(lease, dict) or not fields <= set(lease) or set(lease) - fields - {'release_id'} or lease['issuer'] != 'operator':
                    raise ValueError('explicit operator-provisioned lease required')
                if not isinstance(lease['lease_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',lease['lease_id']):
                    raise ValueError('invalid lease identity')
                issued = timestamp(lease['issued_at']).timestamp(); expires = timestamp(lease['expires_at']).timestamp(); offline = timestamp(lease['offline_until']).timestamp()
                if not issued < offline <= expires or expires - issued > 3600:
                    raise ValueError('local authority must expire within one hour')
                from adapters import uint
                start, end = uint(lease['sequence_start']), uint(lease['sequence_end'])
                if start == 0 or end < start:
                    raise ValueError('invalid reserved command sequence range')
                for previous in ranges.get(rule['target_device_id'], []):
                    if max(start, previous[0]) <= min(end, previous[1]):
                        raise ValueError('overlapping local sequence reservations')
                ranges.setdefault(rule['target_device_id'], []).append((start, end))
        serialized = canonical(bundle)
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT revision,payload FROM rule_bundle WHERE id=1').fetchone()
            if old and (bundle['revision'] < old[0] or (bundle['revision'] == old[0] and serialized != old[1])):
                raise ValueError('policy rollback or conflicting revision')
            for rule in bundle['rules']:
                lease = rule.get('lease')
                if not lease:
                    continue
                fingerprint = hashlib.sha256(canonical({'target':rule['target_device_id'], 'channel':rule['channel_id'], 'lease':lease}).encode()).hexdigest()
                prior = db.execute('SELECT fingerprint FROM rule_leases WHERE lease_id=?', (lease['lease_id'],)).fetchone()
                if prior and prior[0] != fingerprint:
                    raise ValueError('lease identity cannot be reused with changed authority')
                db.execute('INSERT OR IGNORE INTO rule_leases VALUES(?,?,?)', (lease['lease_id'], fingerprint, lease['sequence_start']))
            db.execute('INSERT INTO rule_bundle VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload', (bundle['revision'], serialized))

    def evaluate(self, rule, valid_until, connected, now):
        store = EdgeStore(self.database)
        reason = None
        try:
            target = store.snapshot(rule['target_device_id'], now, rule['maximum_age_seconds'])
            sensor = store.snapshot(rule['sensor_device_id'], now, rule['maximum_age_seconds'])
            if now >= timestamp(valid_until).timestamp():
                reason = 'policy_expired'
            elif target is None or not target['fresh']:
                reason = 'target_unknown_or_stale'
            else:
                state = target['event']
                health = get_reading(state, 'device', 'device.health')
                mode = get_reading(state, rule['channel_id'], 'control.mode')
                hold = get_reading(state, rule['channel_id'], 'control.manual_hold_until')
                if not health or health['quality'] != 'valid' or health['value'] != 'ok':
                    reason = 'fault_or_maintenance_or_unknown'
                elif not mode or mode['quality'] != 'valid' or mode['value'] != 'auto':
                    reason = 'manual_or_maintenance_or_protected'
                elif not hold or hold['quality'] != 'valid' or state['monotonic_ms'] is None or hold['value'] > state['monotonic_ms']:
                    reason = 'manual_hold_or_unknown'
            if reason is None and store.active_manual_hold(rule['target_device_id'], rule['channel_id'], now)['active']:
                reason = 'backend_edge_manual_hold'
            lease = rule.get('lease')
            if reason is None and not lease:
                reason = 'evaluated_not_authorized'
            if reason is None and (now < timestamp(lease['issued_at']).timestamp() or now >= timestamp(lease['expires_at']).timestamp() or (not connected and now >= timestamp(lease['offline_until']).timestamp())):
                reason = 'authority_expired_or_not_started'
            if reason is None and (sensor is None or not sensor['fresh']):
                reason = 'sensor_unknown_or_stale'
            observed = None
            if reason is None:
                observed = get_reading(sensor['event'], 'sensor.radar', 'presence.radar')
                details = observed.get('details', {}) if observed else {}
                trusted = sensor['event']['source_mode'] == 'SIMULATED' or details.get('authenticity') == 'authenticated_gatt_hmac_sha256'
                if not observed or observed['quality'] != 'valid' or type(observed['value']) is not bool or details.get('continuous_occupancy') is not True:
                    reason = 'continuous_occupancy_evidence_unavailable'
                elif not trusted or sensor['event']['source_mode'] != target['event']['source_mode'] or sensor['event']['source_mode'] == 'REPLAYED':
                    reason = 'unauthenticated_or_mixed_source_evidence'
                elif details.get('measurement_age_ms', 0) + sensor['age_seconds'] * 1000 > rule['maximum_age_seconds'] * 1000:
                    reason = 'measurement_stale'
                elif observed['value'] != rule['when_present']:
                    reason = 'condition_not_met'
                elif 'raw_light_below' in rule:
                    light = get_reading(sensor['event'], 'sensor.light', 'illuminance.raw')
                    if not light or light['quality'] not in {'valid','uncalibrated'} or type(light['value']) is not int or light['value'] >= rule['raw_light_below']:
                        reason = 'raw_light_condition_not_met_or_unknown'
            with closing(sqlite3.connect(self.database)) as db, db:
                db.execute('BEGIN IMMEDIATE')
                previous = db.execute('SELECT since,last_received,last_event,last_command_event FROM rule_state WHERE id=?', (rule['id'],)).fetchone()
                since = previous[0] if previous else None
                event_id = sensor['event']['event_id'] if sensor else None
                received = timestamp(sensor['event']['received_at']).timestamp() if sensor else None
                if reason:
                    since = None
                elif since is None or not previous or received - (previous[1] or received) > rule['maximum_age_seconds'] or received < previous[1]:
                    since = received
                db.execute('INSERT INTO rule_state VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET since=excluded.since,last_received=excluded.last_received,last_event=excluded.last_event', (rule['id'], since, received, event_id, previous[3] if previous else None))
                if not reason and received - since < rule['stable_for_seconds']:
                    reason = 'waiting_for_stable_evidence'
                command = None
                if not reason:
                    desired = get_reading(target['event'], rule['channel_id'], 'relay.commanded')
                    if not desired or desired['quality'] != 'valid':
                        reason = 'requested_state_unknown'
                    elif desired['value'] == rule['desired_on']:
                        reason = 'already_requested_state_no_replay'
                    elif previous and previous[3] == event_id:
                        reason = 'sample_already_evaluated_no_replay'
                    else:
                        next_seq = db.execute('SELECT next_sequence FROM rule_leases WHERE lease_id=?', (lease['lease_id'],)).fetchone()
                        if not next_seq or int(next_seq[0]) > int(lease['sequence_end']):
                            reason = 'sequence_lease_exhausted'
                        else:
                            seq = next_seq[0]
                            expiry = min(now + 20, timestamp(lease['expires_at']).timestamp(), timestamp(valid_until).timestamp(), timestamp(lease['offline_until']).timestamp() if not connected else float('inf'))
                            authority = {'kind':'local_rule', 'rule_id':rule['id'], 'lease_id':lease['lease_id'], 'lease_expires_at':iso(expiry)}
                            if lease.get('release_id'):
                                authority['release_id'] = lease['release_id']
                            command = validate_command({'schema_version':1, 'id':'local-' + hashlib.sha256((rule['id'] + event_id + seq).encode()).hexdigest()[:32], 'device_id':rule['target_device_id'], 'product_family':target['event']['product_family'], 'channel_id':rule['channel_id'], 'capability':'relay.commanded', 'value':rule['desired_on'], 'sequence':seq, 'issued_at':iso(now), 'expires_at':iso(expiry), 'boot_id':target['event']['boot_id'], 'source_mode':target['event']['source_mode'], 'authority':authority})
                            db.execute('UPDATE rule_leases SET next_sequence=? WHERE lease_id=?', (str(int(seq)+1), lease['lease_id']))
                            db.execute('UPDATE rule_state SET last_command_event=? WHERE id=?', (event_id, rule['id']))
                            reason = 'authorized_candidate'
                db.execute('INSERT INTO rule_evaluations VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,reason=excluded.reason,updated=excluded.updated', (rule['id'], 'candidate' if command else 'held', reason, now))
            return {'rule_id':rule['id'], 'reason':reason, 'command':command}
        finally:
            store.close()

    def once(self, connected=False, now=None):
        now = time.time() if now is None else now
        with closing(sqlite3.connect(self.database)) as db, db:
            row = db.execute('SELECT payload FROM rule_bundle WHERE id=1').fetchone()
        if row is None:
            return []
        bundle = json.loads(row[0])
        return [self.evaluate(rule, bundle['valid_until'], connected, now) for rule in bundle['rules']]
