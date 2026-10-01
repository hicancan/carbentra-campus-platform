"""Durable command delivery, default disabled. This release permits only explicitly
registered VIRTUAL + SIMULATED endpoints by default. A future PHYSICAL path
requires independent exact opt-in and matching per-device release records.
A broker PUBACK proves transport acceptance only, not device execution.
"""
from contextlib import closing
import datetime
import json
import math
import re
import sqlite3
import time
import urllib.parse
from platform_http import PlatformHTTP
from wire import ID,SEQUENCE


def wire_command(wire,device):
    fields={'id','device_id','profile_id','seq','issued_s','expires_s','action'}
    if not isinstance(wire,dict) or set(wire)!=fields or wire.get('device_id') != device:
        raise ValueError('invalid command envelope')
    for key in ('id','device_id','profile_id'):
        if not isinstance(wire[key],str) or not ID.fullmatch(wire[key]):raise ValueError('invalid command identity')
    seq=wire['seq']
    if not isinstance(seq,str) or not SEQUENCE.fullmatch(seq) or int(seq)>=2**64:raise ValueError('invalid command sequence')
    if any(type(wire[k]) is not int or not 0<wire[k]<=2**53-1 for k in ('issued_s','expires_s')) or not 0<wire['expires_s']-wire['issued_s']<=60:
        raise ValueError('invalid command window')
    if not isinstance(wire['action'],str) or wire['action'] not in {'hold','shed','restore'}:raise ValueError('unsupported action')
    return json.dumps(wire,sort_keys=True,separators=(',',':'))


class CommandTransport:
    def __init__(self,database,allowed_devices,virtual_devices,publisher,reporter=None,http=None,ready=None,physical_enabled=False,physical_releases=None):
        self.database=database;self.allowed=set(allowed_devices);self.virtual=set(virtual_devices)
        if not self.virtual<=self.allowed or not all(isinstance(d,str) and ID.fullmatch(d) for d in self.allowed):raise ValueError('invalid virtual-device allowlist')
        if type(physical_enabled) is not bool:raise ValueError('physical enablement must be an explicit boolean')
        releases={} if physical_releases is None else physical_releases
        if not isinstance(releases,dict) or not set(releases)<=self.allowed or not all(isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9:_.-]{1,200}',value) for value in releases.values()):raise ValueError('invalid per-device physical release allowlist')
        if physical_enabled and not releases:raise ValueError('physical dispatch requires explicit per-device release records')
        if self.virtual & set(releases):raise ValueError('a device cannot be both virtual and physical')
        self.physical_enabled=physical_enabled;self.physical_releases=dict(releases)
        self.publisher=publisher;self.http=http;self.ready=ready or (lambda:True);self.reporter=reporter or self.report
        with closing(sqlite3.connect(database)) as db, db:
            db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
            db.execute('''CREATE TABLE IF NOT EXISTS command_inbox(
                id TEXT PRIMARY KEY, device TEXT NOT NULL, seq TEXT NOT NULL, wire TEXT NOT NULL,
                state TEXT NOT NULL, reason TEXT, updated REAL NOT NULL)''')
    def report(self,identity,lease_id,status,reason):
        if self.http is None:raise ValueError('platform is unconfigured')
        payload={'lease_id':lease_id,'status':status}
        if reason:payload['reason']=reason
        response=self.http.request('POST','/api/v1/adapter/commands/'+urllib.parse.quote(identity,safe='')+'/delivery',json.dumps(payload,separators=(',',':')))
        data=response.get('data') if isinstance(response,dict) else None
        if not isinstance(data,dict) or data.get('durable') is not True or data.get('id')!=identity:raise ValueError('delivery receipt not durable')
    def process(self,item,now=None):
        started=time.monotonic()
        now=time.time() if now is None else now
        if type(now) not in (int,float) or not math.isfinite(now):raise ValueError('invalid time')
        if not isinstance(item,dict):raise ValueError('invalid leased command')
        device=item.get('device_id');identity=item.get('id');lease=item.get('lease_id')
        if not isinstance(lease,str) or not 1<=len(lease)<=128 or not isinstance(identity,str) or not ID.fullmatch(identity):raise ValueError('invalid lease identity')
        wire=item.get('wire');canonical=wire_command(wire,device)
        if identity!=wire['id']:raise ValueError('command identity mismatch')
        try:lease_until=datetime.datetime.fromisoformat(item['lease_expires_at'].replace('Z','+00:00'))
        except (KeyError,ValueError,TypeError,AttributeError) as error:raise ValueError('invalid lease deadline') from error
        if lease_until.tzinfo is None:raise ValueError('lease timezone required')
        status=reason=None
        virtual=device in self.virtual and item.get('source_mode')=='SIMULATED' and item.get('dispatch_mode')=='VIRTUAL'
        physical=self.physical_enabled and item.get('source_mode')=='REAL' and item.get('dispatch_mode')=='PHYSICAL' and device in self.physical_releases and item.get('release_id')==self.physical_releases[device]
        if device not in self.allowed or not (virtual or physical) or item.get('transport')!='MQTT':
            status,reason='failed','dispatch_disabled_or_release_not_allowlisted'
        elif now>=wire['expires_s'] or now>=lease_until.timestamp():status,reason='expired','command_or_lease_expired'
        elif now<wire['issued_s']:status,reason='failed','future_command'
        db=sqlite3.connect(self.database,timeout=5)
        try:
            db.execute('PRAGMA synchronous=FULL')
            with db:
                existing=db.execute('SELECT device,seq,wire,state,reason FROM command_inbox WHERE id=?',(identity,)).fetchone()
                if existing and existing[:3]!=(device,wire['seq'],canonical):
                    status,reason='failed','conflicting_command_identity'
                elif existing:
                    # Never replay a command after a crash or ambiguous PUBACK.
                    state,old_reason=existing[3:]
                    status=state if state in {'published','failed','expired'} else 'failed'
                    reason=old_reason if state in {'published','failed','expired'} else 'mqtt_delivery_uncertain'
                elif status is None:
                    prior=db.execute("SELECT seq FROM command_inbox WHERE device=? AND state IN ('sending','published','uncertain')",(device,)).fetchall()
                    if any(int(seq[0])>=int(wire['seq']) for seq in prior):status,reason='failed','replayed_sequence'
                    db.execute('INSERT INTO command_inbox VALUES(?,?,?,?,?,?,?)',(identity,device,wire['seq'],canonical,'received' if status is None else status,reason,now))
                else:
                    db.execute('INSERT OR IGNORE INTO command_inbox VALUES(?,?,?,?,?,?,?)',(identity,device,wire['seq'],canonical,status,reason,now))
            if status is None:
                with db:db.execute("UPDATE command_inbox SET state='sending',updated=? WHERE id=?",(now,identity))
                # Commit before touching MQTT. A crash here becomes unknown, never a blind resend.
                if time.monotonic()-started >= min(wire['expires_s'],lease_until.timestamp())-now:
                    status,reason='expired','command_or_lease_expired_before_publish'
                    with db:db.execute('UPDATE command_inbox SET state=?,reason=?,updated=? WHERE id=?',(status,reason,now,identity))
                    self.reporter(identity,lease,status,reason)
                    return {'id':identity,'status':status,'reason':reason}
                try:published=self.publisher('carbentra/v1/'+device+'/cmd',canonical)
                except Exception:published=False
                status,reason=('published',None) if published is True else ('failed','mqtt_delivery_uncertain')
                with db:db.execute('UPDATE command_inbox SET state=?,reason=?,updated=? WHERE id=?',('published' if published is True else 'uncertain',reason,now,identity))
            self.reporter(identity,lease,status,reason)
            return {'id':identity,'status':status,'reason':reason}
        finally:db.close()
    def once(self):
        if not (self.virtual or (self.physical_enabled and self.physical_releases)) or self.http is None or not self.ready():return 0
        response=self.http.request('GET','/api/v1/adapter/commands?limit=20')
        items=response.get('data') if isinstance(response,dict) else None
        if not isinstance(items,list) or len(items)>20:raise ValueError('invalid command batch')
        for item in items:
            if not self.ready():break
            self.process(item)
        return len(items)
    def run(self):
        while True:
            try:self.once()
            except (OSError,ValueError,sqlite3.Error):pass
            time.sleep(1)
