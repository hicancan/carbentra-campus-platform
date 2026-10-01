"""Durable HTTP transport outbox. Campus identity, energy and control stay in platform.
A committed edge receipt means edge durability; platform delivery is separately
tracked. Retries keep raw bytes/identity, and no command is dispatched here.
"""
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from service import strict_json

from platform_http import PlatformHTTP

class Forwarder:
    def __init__(self,database,origin,token,sender=None):
        self.database=database;self.http=PlatformHTTP(origin,token)
        self.sender=sender or self.send;self.last_attempt_succeeded=False
    def send(self,kind,payload):
        paths={'event':'/api/v1/ingest/events','ack':'/api/v1/ingest/ack','switch_ack':'/api/v1/ingest/channel-acks'}
        if kind not in paths:raise ValueError('unsupported outbox kind')
        path=paths[kind]
        return self.http.request('POST',path,payload)
    def once(self,now=None):
        self.last_attempt_succeeded=False
        now=time.time() if now is None else now
        db=sqlite3.connect(self.database,timeout=5)
        try:
            row=db.execute('SELECT event_key,kind,payload,attempts FROM forwarding WHERE delivered=0 AND blocked=0 AND next_attempt<=? ORDER BY rowid LIMIT 1',(now,)).fetchone()
            if row is None:return False
            key,kind,payload,attempts=row
            try:raw=strict_json(payload,maximum=65536)
            except (ValueError,UnicodeError):
                with db:db.execute("UPDATE forwarding SET blocked=1,last_error='stored_payload_invalid' WHERE event_key=?",(key,))
                return True
            try:
                response=self.sender(kind,payload)
                data=response.get('data') if isinstance(response,dict) else None
                if not isinstance(data,dict) or data.get('durable') is not True or data.get('device_id') != raw['device_id']:
                    raise ValueError('no matching durable platform receipt')
                if kind == 'event' and (data.get('event_id') != raw['event_id'] or data.get('boot_id') != raw['boot_id'] or data.get('sequence') != raw['sequence']):
                    raise ValueError('wrong platform sample receipt')
                if kind in {'ack','switch_ack'} and (data.get('id',data.get('command_id')) != raw['id'] or data.get('seq') != raw['seq']):
                    raise ValueError('wrong platform command receipt')
                with db:db.execute('UPDATE forwarding SET delivered=1,last_error=NULL WHERE event_key=?',(key,))
                self.last_attempt_succeeded=True
            except (OSError,ValueError,TypeError) as error:
                # Conflicts are retained for operator review, never overwritten.
                blocked=isinstance(error,urllib.error.HTTPError) and error.code==409
                with db:db.execute('UPDATE forwarding SET attempts=attempts+1,next_attempt=?,blocked=?,last_error=? WHERE event_key=?',(now+min(300,2**min(attempts,8)),int(blocked),type(error).__name__,key))
            return True
        finally:db.close()
    def run(self):
        while True:
            try:
                if self.once() and self.last_attempt_succeeded:continue
            except sqlite3.Error:pass  # Retain all rows and retry after transient storage contention.
            time.sleep(0.2)
