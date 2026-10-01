"""Loopback-only real Mosquitto mTLS + unified gateway + 6 virtual devices proof.

The HTTP peer is a durable contract sink, not the real campus backend. Its result
proves transport/restart scope only; backend integration is a separate gate.
Ephemeral test certificates stay in TemporaryDirectory and are removed at exit.
"""
from __future__ import annotations
from contextlib import closing
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from contract import canonical, validate_event, validate_switch_ack
from store import EdgeStore
from service import strict_json
from wire import validate_ack
from virtual_bridge import VirtualRoom
from dataclasses import asdict, replace

EDGE=Path(__file__).resolve().parents[1]
TOKEN='synthetic-loopback-integration-token'

def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def certificates(root):
    now=datetime.now(timezone.utc);key=ec.generate_private_key(ec.SECP256R1())
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Ephemeral integration CA')])
    ca=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(hours=2)).add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).sign(key,hashes.SHA256())
    (root/'ca.pem').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    for cn in ('localhost','edge-test','virtual-test'):
        leaf_key=ec.generate_private_key(ec.SECP256R1())
        builder=x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,cn)])).issuer_name(name).public_key(leaf_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(hours=2)).add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
        if cn=='localhost':builder=builder.add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
        cert=builder.sign(key,hashes.SHA256())
        (root/(cn+'.pem')).write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        path=root/(cn+'.key');path.write_bytes(leaf_key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));path.chmod(0o600)

def wait_until(predicate,seconds=25):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.1)
    raise AssertionError('integration outcome timed out')

def main():
    p=argparse.ArgumentParser();p.add_argument('--mosquitto',required=True);p.add_argument('--library-path');p.add_argument('--output',type=Path,default=EDGE/'mqtt-integration.json');args=p.parse_args()
    evidence={'scope':'real loopback Mosquitto mTLS + platform edge runtime + virtual 3-family/2-room bridge + durable HTTP contract sink; no actual campus backend, RF, hardware or mains', 'recorded_at_utc':datetime.now(timezone.utc).isoformat()}
    sources=[*(EDGE.parent/'packages/iot-contract').glob('*.json'),*(EDGE.parent/'packages/iot-contract').glob('protocols/*.json'),*EDGE.glob('*.py'),Path(__file__),*(EDGE.parent/'packages/iot-contract').glob('python/**/*.py'),*(EDGE.parent/'packages/iot-contract').glob('schemas/**/*.json')]
    def fingerprints():return {path.relative_to(EDGE.parent).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(sources)}
    before=fingerprints()
    with tempfile.TemporaryDirectory(prefix='carbentra-edge-network-') as temp:
        root=Path(temp);certificates(root);mqtt_port=port();http_port=port();database=root/'edge.sqlite';sink_db=root/'sink.sqlite'
        EdgeStore(sink_db).close();offline=threading.Event();received=[];deliveries=[];command_state={};lock=threading.Lock()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def answer(self,status,data):
                body=canonical({'data':data}).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            def authorized(self):
                if self.headers.get('Authorization')!='Bearer '+TOKEN:self.answer(401,{});return False
                if offline.is_set():self.answer(503,{});return False
                return True
            def do_POST(self):
                if not self.authorized():return
                raw=strict_json(self.rfile.read(int(self.headers['Content-Length'])),maximum=32768)
                if self.path=='/api/v1/ingest/events':
                    validate_event(raw);store=EdgeStore(sink_db)
                    try:receipt=store.accept_event(raw)
                    finally:store.close()
                    with lock:received.append(raw)
                    self.answer(200,receipt)
                elif self.path in {'/api/v1/ingest/ack','/api/v1/ingest/channel-acks'}:
                    if self.path.endswith('channel-acks'):validate_switch_ack(raw);kind='switch_ack'
                    else:validate_ack(raw,raw['device_id']);kind='ack'
                    store=EdgeStore(sink_db)
                    try:store.accept_ack(kind,raw['device_id'],raw)
                    finally:store.close()
                    self.answer(200,{'durable':True,'device_id':raw['device_id'],'id':raw['id'],'seq':raw['seq']})
                elif self.path.endswith('/delivery'):
                    cid=self.path.split('/')[-2]
                    with lock:deliveries.append({'id':cid,**raw})
                    self.answer(200,{'durable':True,'id':cid})
                else:self.answer(404,{})
            def do_GET(self):
                if not self.authorized():return
                if not self.path.startswith('/api/v1/adapter/commands?'):self.answer(404,{});return
                with lock:
                    plug=next((e for e in received if e['product_family']=='PLUG'),None)
                    if plug and not command_state:
                        now=int(time.time());device=plug['device_id'];cid='network-proof-001'
                        command_state.update(id=cid,device_id=device,source_mode='SIMULATED',dispatch_mode='VIRTUAL',transport='MQTT',lease_id='network-proof-lease',lease_expires_at=datetime.fromtimestamp(now+25,timezone.utc).isoformat(),wire={'id':cid,'device_id':device,'profile_id':'lab-load','seq':'1','issued_s':now,'expires_s':now+30,'action':'shed'})
                    item=dict(command_state) if command_state else None
                self.answer(200,[item] if item else [])
        server=ThreadingHTTPServer(('127.0.0.1',http_port),Handler);server_thread=threading.Thread(target=server.serve_forever,daemon=True);server_thread.start()
        (root/'acl').write_text('user edge-test\ntopic read carbentra/#\ntopic write carbentra/+/+/receipt\ntopic write carbentra/+/+/time\ntopic write carbentra/+/+/cmd\ntopic write carbentra/+/+/command\nuser virtual-test\ntopic read carbentra/+/+/cmd\ntopic read carbentra/+/+/command\ntopic write carbentra/#\n', encoding="utf-8")
        (root/'mosquitto.conf').write_text(f'listener {mqtt_port} 127.0.0.1\nallow_anonymous false\nrequire_certificate true\nuse_identity_as_username true\ncafile {root}/ca.pem\ncertfile {root}/localhost.pem\nkeyfile {root}/localhost.key\nacl_file {root}/acl\npersistence false\n', encoding="utf-8")
        rooms=[VirtualRoom('a101'),VirtualRoom('a102')];records=[]
        for i,room in enumerate(rooms):
            for e in room.enrollments:
                if e.ble_address:e=replace(e,ble_address=f'AA:BB:CC:DD:EE:{i+1:02X}')
                records.append({k:v for k,v in asdict(e).items() if v is not None})
        (root/'devices.json').write_text(canonical({'enrollments':records}), encoding="utf-8")
        env={**os.environ,'CARBENTRA_ADAPTER_TOKEN':TOKEN,'CARBENTRA_ENABLE_PHYSICAL_DISPATCH':'false','CARBENTRA_PHYSICAL_RELEASES_JSON':'{}'}
        if args.library_path:env['LD_LIBRARY_PATH']=args.library_path
        processes=[];logs=[]
        def start(cmd,label):
            log=open(root/(label+'.log'),'w+');logs.append(log);process=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT);processes.append(process);return process
        def start_edge():return start([sys.executable,str(EDGE/'service.py'),'--broker','localhost','--port',str(mqtt_port),'--ca',str(root/'ca.pem'),'--certificate',str(root/'edge-test.pem'),'--key',str(root/'edge-test.key'),'--devices',str(root/'devices.json'),'--database',str(database),'--platform-url',f'http://127.0.0.1:{http_port}','--enable-virtual-commands'],'edge-'+str(len(processes)))
        try:
            broker=start([args.mosquitto,'-c',str(root/'mosquitto.conf')], 'broker');time.sleep(.25)
            if broker.poll() is not None:raise AssertionError('Mosquitto failed startup')
            edge=start_edge()
            bridge=start([sys.executable,str(EDGE/'virtual_bridge.py'),'--broker','localhost','--port',str(mqtt_port),'--ca',str(root/'ca.pem'),'--certificate',str(root/'virtual-test.pem'),'--key',str(root/'virtual-test.key'),'--interval','.3'], 'bridge')
            wait_until(lambda:len({e['device_id'] for e in received})==6)
            def ack_count():
                with closing(sqlite3.connect(sink_db)) as db, db:return db.execute('SELECT count(*) FROM wire_acks').fetchone()[0]
            wait_until(lambda:ack_count()>=1 and any(d['status']=='published' for d in deliveries))
            evidence.update(devices=len({e['device_id'] for e in received}),families=sorted({e['product_family'] for e in received}),all_sources_simulated=all(e['source_mode']=='SIMULATED' for e in received),virtual_command_delivery='published',virtual_device_ack='OBSERVED_VERIFIED_simulated_only')
            offline.set();time.sleep(1)
            with closing(sqlite3.connect(database)) as db, db:pending_before=db.execute('SELECT count(*) FROM forwarding WHERE delivered=0').fetchone()[0]
            if pending_before==0:raise AssertionError('outbox did not preserve offline data')
            edge.terminate();edge.wait(timeout=10);edge=start_edge();time.sleep(.7)
            offline.clear()
            # Stop producers so durable backlog can settle while gateway keeps running.
            bridge.terminate();bridge.wait(timeout=10)
            def drained():
                with closing(sqlite3.connect(database)) as db, db:return db.execute('SELECT count(*) FROM forwarding WHERE delivered=0').fetchone()[0]==0
            wait_until(drained)
            if ack_count()!=1:raise AssertionError('ambiguous/restarted command was replayed')
            evidence.update(offline_pending_preserved=pending_before,restart_outbox_drained=True,no_command_replay=True,success=True)
        except Exception as error:
            evidence.update(success=False,error=str(error))
            for log in logs:log.flush();log.seek(0);print(log.name+'\n'+log.read(),file=sys.stderr)
            raise
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
            for log in logs:log.close()
            server.shutdown();server.server_close()
            evidence['source_sha256']=fingerprints()
            evidence['source_sha256_before']=before
            evidence['changed_during_run']=before!=fingerprints()
            evidence['success']=evidence.get('success',False) and not evidence['changed_during_run']
            args.output.write_text(json.dumps(evidence,indent=2)+'\n', encoding="utf-8")
    if not evidence['success']:raise SystemExit('Source changed during integration or test failed; rerun against a stable tree')
    print(json.dumps(evidence,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
