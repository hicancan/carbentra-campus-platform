"""Generate a persisted DB using an actual historical Git Edge implementation,
then prove one-time canonical migration preserves raw identity/time/receipts.
The historical code is temporary test input, never a second deployment source.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adapters import Enrollment,iso
from migrations import migrate_legacy_outbox
from store import EdgeStore
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--hardware-repo',type=Path,required=True);p.add_argument('--revision',required=True);p.add_argument('--output',type=Path,default=ROOT/'migration-integration.json');args=p.parse_args()
def git(*command):return subprocess.check_output(['git','-C',str(args.hardware_repo),*command])
revision=git('rev-parse','--verify',args.revision).decode().strip()
files=['edge/service.py','edge/wire.py','contracts/device-wire-v2.schema.json','contracts/device-ack-v2.schema.json','contracts/examples/device-telemetry-v2.json']
record={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'actual historical Git implementation creates SQLite; current versioned migration preserves synthetic fixture evidence; no physical IO','historical_revision':revision}
current=[*ROOT.glob('*.py'),*(ROOT.parent/'packages/iot-contract/python').glob('**/*.py'),*(ROOT.parent/'packages/iot-contract/schemas').glob('**/*.json'),*(ROOT.parent/'packages/iot-contract').glob('*.json'),Path(__file__)]
def fingerprints():return {path.relative_to(ROOT.parent).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(current)}
before=fingerprints()
with tempfile.TemporaryDirectory(prefix='carbentra-historical-edge-') as directory:
    root=Path(directory);old_hashes={}
    for name in files:
        data=git('show',revision+':'+name);target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);old_hashes[name]=hashlib.sha256(data).hexdigest()
    database=root/'actual-old-edge.sqlite'
    script='''
import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from service import Edge
root=Path(sys.argv[1]).parent
raw=json.loads((root/'contracts/examples/device-telemetry-v2.json').read_text())
edge=Edge(sys.argv[2],[raw['device_id']])
receipts=[]
for seq in (1,2):
 raw['sample_seq']=str(seq)
 receipts.append(edge.accept('carbentra/v1/'+raw['device_id']+'/telemetry',json.dumps(raw),1750000000.125+seq-1)[1])
with edge.db:
 edge.db.execute("UPDATE forwarding SET delivered=1 WHERE json_extract(payload,'$.sample_seq')='2'")
edge.db.close()
print(json.dumps({'device_id':raw['device_id'],'receipts':receipts}))
'''
    generated=json.loads(subprocess.check_output([sys.executable,'-c',script,str(root/'edge'),str(database)],text=True))
    store=EdgeStore(database)
    try:
        originals=store.db.execute('SELECT device,epoch,seq,received,payload FROM telemetry ORDER BY seq').fetchall()
        schema_before=store.db.execute("SELECT name,sql FROM sqlite_master WHERE name IN ('telemetry','forwarding','acknowledgements') ORDER BY name").fetchall()
        result=migrate_legacy_outbox(store,[Enrollment(generated['device_id'],'PLUG','plug-wire-v2','SIMULATED')])
        assert result['converted_pending']==1 and result['archived_delivered']==1 and result['quarantined']==0,result
        assert store.db.execute('SELECT device,epoch,seq,received,payload FROM telemetry ORDER BY seq').fetchall()==originals
        event=json.loads(store.db.execute('SELECT payload FROM iot_events').fetchone()[0])
        assert event['received_at']==iso(1750000000.125)
        assert event['raw']==json.loads(originals[0][4])
        assert (event['boot_id'],event['sequence'])==(generated['receipts'][0]['boot_epoch'],generated['receipts'][0]['sample_seq'])
        assert store.db.execute("SELECT count(*) FROM forwarding WHERE kind='telemetry'").fetchone()[0]==0
        assert migrate_legacy_outbox(store,[Enrollment(generated['device_id'],'PLUG','plug-wire-v2','SIMULATED')])['already_applied']
        record.update(success=True,migration=result,original_raw_rows_unchanged=True,original_receipt_time_preserved=True,original_device_receipt_identity_preserved=True,second_run_idempotent=True,historical_source_sha256=old_hashes,legacy_schema=schema_before)
    finally:store.close()
record['source_sha256_before']=before;record['source_sha256']=fingerprints();record['changed_during_run']=before!=fingerprints();record['success']=record['success'] and not record['changed_during_run']
args.output.write_text(json.dumps(record,indent=2)+'\n', encoding="utf-8")
print(json.dumps({k:v for k,v in record.items() if k not in {'source_sha256','source_sha256_before','historical_source_sha256','legacy_schema'}},indent=2))
raise SystemExit(0 if record['success'] else 1)
