"""Actual FastAPI HTTP -> durable edge -> real MQTT -> 3-gang virtual Switch -> ACK.

All endpoints are loopback and SIMULATED. This test uses the real backend app,
not a contract sink, with an isolated development SQLite database. PostgreSQL,
physical devices/RF, mains and deployment qualification are outside its scope.
"""
from contextlib import closing
from datetime import datetime, timezone
from dataclasses import asdict, replace
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import http.cookiejar
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.check_mqtt_multidevice import certificates, port, wait_until
from virtual_bridge import VirtualRoom
from contract import canonical
ROOT=Path(__file__).resolve().parents[2];EDGE=ROOT/'edge'
TOKEN='synthetic-actual-backend-network-test-token'


def main():
    p=argparse.ArgumentParser();p.add_argument('--mosquitto',required=True);p.add_argument('--library-path');p.add_argument('--backend-python',required=True);p.add_argument('--output',type=Path,default=EDGE/'backend-integration.json');args=p.parse_args()
    evidence={'scope':'actual FastAPI HTTP auth/ingest/command/adapter/ACK + edge + real loopback Mosquitto mTLS + three-family/two-room simulator; SQLite development test, no RF or physical mains','recorded_at_utc':datetime.now(timezone.utc).isoformat()}
    paths=[*(ROOT/'packages/iot-contract').glob('*.json'),*(ROOT/'packages/iot-contract').glob('protocols/*.json'),*EDGE.glob('*.py'),*(ROOT/'backend/app').glob('*.py'),Path(__file__),EDGE/'tools/backend_fixture.py',*(ROOT/'packages/iot-contract').glob('python/**/*.py'),*(ROOT/'packages/iot-contract').glob('schemas/**/*.json')]
    def fingerprints():return {path.relative_to(ROOT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}
    before=fingerprints()
    with tempfile.TemporaryDirectory(prefix='carbentra-actual-backend-') as temp:
        root=Path(temp);certificates(root);mqtt_port=port();http_port=port();backend_db=root/'backend.sqlite';edge_db=root/'edge.sqlite'
        (root/'acl').write_text('user edge-test\ntopic read carbentra/#\ntopic write carbentra/+/+/receipt\ntopic write carbentra/+/+/time\ntopic write carbentra/+/+/cmd\ntopic write carbentra/+/+/command\nuser virtual-test\ntopic read carbentra/+/+/cmd\ntopic read carbentra/+/+/command\ntopic write carbentra/#\n', encoding="utf-8")
        (root/'broker.conf').write_text(f'listener {mqtt_port} 127.0.0.1\nallow_anonymous false\nrequire_certificate true\nuse_identity_as_username true\ncafile {root}/ca.pem\ncertfile {root}/localhost.pem\nkeyfile {root}/localhost.key\nacl_file {root}/acl\npersistence false\n', encoding="utf-8")
        devices=[]
        for i,name in enumerate(('a101','a102')):
            for device in VirtualRoom(name).enrollments:
                if device.ble_address:device=replace(device,ble_address=f'AA:BB:CC:DD:EE:{i+1:02X}')
                devices.append({k:v for k,v in asdict(device).items() if v is not None})
        (root/'devices.json').write_text(canonical({'enrollments':devices}), encoding="utf-8")
        env={**os.environ,'CARBENTRA_ADAPTER_TOKEN':TOKEN,'CARBENTRA_ENABLE_PHYSICAL_DISPATCH':'false','CARBENTRA_PHYSICAL_RELEASES_JSON':'{}','CARBENTRA_TEST_LOSE_FIRST_DELIVERY':'true'}
        if args.library_path:env['LD_LIBRARY_PATH']=args.library_path
        processes=[];logs=[]
        def start(command,label):
            stream=open(root/(label+'.log'),'w+');logs.append(stream)
            child=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,env=env);processes.append(child);return child
        origin=f'http://127.0.0.1:{http_port}'
        opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),urllib.request.ProxyHandler({}))
        def request(method,path,body=None,headers=None):
            req=urllib.request.Request(origin+path,data=canonical(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**(headers or {})},method=method)
            try:
                with opener.open(req,timeout=5) as response:return response.status,json.load(response)
            except urllib.error.HTTPError as error:return error.code,json.load(error)
        def query(sql,args=()):
            if not backend_db.exists():return []
            try:
                with closing(sqlite3.connect(backend_db)) as db, db:return db.execute(sql,args).fetchall()
            except sqlite3.OperationalError:return []
        try:
            backend=start([args.backend_python,str(EDGE/'tools/backend_fixture.py'),'--database',str(backend_db),'--port',str(http_port)],'backend')
            wait_until(lambda:bool(query('SELECT id FROM devices')),20)
            status,response=request('POST','/api/v1/auth/login',{'username':'admin','password':'development-only'})
            if status!=200:raise AssertionError(('login',status,response))
            csrf=response['data']['csrf_token']
            broker=start([args.mosquitto,'-c',str(root/'broker.conf')],'broker');time.sleep(.25)
            edge=start([sys.executable,str(EDGE/'service.py'),'--broker','localhost','--port',str(mqtt_port),'--ca',str(root/'ca.pem'),'--certificate',str(root/'edge-test.pem'),'--key',str(root/'edge-test.key'),'--devices',str(root/'devices.json'),'--database',str(edge_db),'--platform-url',origin,'--enable-virtual-commands'],'edge')
            bridge=start([sys.executable,str(EDGE/'virtual_bridge.py'),'--broker','localhost','--port',str(mqtt_port),'--ca',str(root/'ca.pem'),'--certificate',str(root/'virtual-test.pem'),'--key',str(root/'virtual-test.key'),'--interval','.3'],'bridge')
            wait_until(lambda:len(query('SELECT DISTINCT device_id FROM hardware_events'))==6,25)
            command_ids=[]
            for gang in (1,2,3):
                payload={'device_id':'virtual-switch-a101','channel_id':f'virtual-switch-a101:relay.{gang}','action':'restore','expires_in_seconds':30,'reason':'Explicit synthetic network integration single-channel control','manual_hold_seconds':60}
                status,response=request('POST','/api/v1/commands',payload,{'X-CSRF-Token':csrf,'Idempotency-Key':f'network-switch-gang-{gang}-001'})
                if status!=201:raise AssertionError(('command_create',gang,status,response))
                command_ids.append(response['data']['id'])
            def terminal():
                rows=query('SELECT status FROM commands WHERE id IN (?,?,?)',command_ids)
                return len(rows)==3 and all(r[0] in ('acknowledged_unverified','rejected','failed','timed_out') for r in rows)
            wait_until(terminal,25)
            wait_until(lambda:len(query('SELECT id FROM commands WHERE delivery_receipt IS NOT NULL'))==3,10)
            commands=query('SELECT id,status,sequence,channel_key FROM commands ORDER BY sequence')
            receipt_rows=query('SELECT history,delivery_receipt FROM commands')
            late_receipts=0
            for history,receipt in receipt_rows:
                terminal_at=next(item['at'] for item in json.loads(history) if item['status']=='acknowledged_unverified')
                if datetime.fromisoformat(json.loads(receipt)['received_at'].replace('Z','+00:00')) >= datetime.fromisoformat(terminal_at.replace('Z','+00:00')):late_receipts+=1
            if late_receipts!=3:raise AssertionError('did not establish ACK-before-delivery-receipt for every command')
            if any(row[1]!='acknowledged_unverified' for row in commands):raise AssertionError(('unexpected command outcomes',commands))
            acks=query('SELECT channel_number,result,raw_payload FROM channel_acknowledgements ORDER BY id')
            if {row[0] for row in acks}!={1,2,3} or any(row[1]!='commanded' or json.loads(row[2])['physical_verification'] is not False for row in acks):raise AssertionError(('wrong ACK scope/truth',acks))
            wait_until(lambda:bool(query("SELECT id FROM channel_observations WHERE channel_id='virtual-switch-a101:relay.2' AND json_extract(value,'$.actuator_reported_on')=1")),10)
            gang_rows=query("SELECT value FROM channel_observations WHERE channel_id LIKE 'virtual-switch-a101:relay.%'")
            if any('active_power_w' in json.loads(row[0]) for row in gang_rows):raise AssertionError('aggregate Switch power was duplicated onto relay gangs')
            status,response=request('GET','/api/v1/commands/'+command_ids[0])
            if status!=200 or response['data']['status']!='acknowledged_unverified':raise AssertionError(('public command response',status,response))
            # An unspecified multi-gang target must remain invalid.
            status,response=request('POST','/api/v1/commands',{'device_id':'virtual-switch-a101','action':'shed','reason':'Synthetic missing-target rejection'}, {'X-CSRF-Token':csrf,'Idempotency-Key':'network-switch-no-channel-001'})
            if status not in (409,422):raise AssertionError(('whole-device switch accepted',status,response))
            with closing(sqlite3.connect(edge_db)) as db, db:
                hold_count=db.execute('SELECT count(*) FROM edge_manual_holds').fetchone()[0]
            if hold_count!=3:raise AssertionError('bounded channel holds not persisted by edge')
            evidence.update(success=True,devices=6,rooms=2,command_statuses=[r[1] for r in commands],target_channels=[r[3] for r in commands],ack_channels=sorted({r[0] for r in acks}),independent_feedback_claimed=False,unspecified_switch_target_rejected=True,edge_channel_holds_persisted=hold_count,switch_aggregate_power_not_duplicated=True,late_delivery_receipt_preserved_terminal_ack=late_receipts)
        except Exception as error:
            evidence.update(success=False,error=str(error))
            for stream in logs:stream.flush();stream.seek(0);print(stream.name+'\n'+stream.read(),file=sys.stderr)
            if edge_db.exists():
                with closing(sqlite3.connect(edge_db)) as db, db:
                    for table in ('forwarding','command_inbox'):
                        try:print(table,db.execute(f'SELECT * FROM {table} LIMIT 5').fetchall(),file=sys.stderr)
                        except sqlite3.Error:pass
            raise
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
            for stream in logs:stream.close()
            evidence['source_sha256']=fingerprints()
            evidence['source_sha256_before']=before
            evidence['changed_during_run']=before!=fingerprints()
            evidence['success']=evidence.get('success',False) and not evidence['changed_during_run']
            args.output.write_text(json.dumps(evidence,indent=2)+'\n', encoding="utf-8")
    if not evidence['success']:raise SystemExit('Source changed during integration or test failed; rerun against a stable tree')
    print(json.dumps({k:v for k,v in evidence.items() if k not in {'source_sha256','source_sha256_before'}},indent=2))

if __name__=='__main__':main()
