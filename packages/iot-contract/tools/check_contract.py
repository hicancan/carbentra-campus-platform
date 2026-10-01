"""Validate authoritative schema syntax, examples, product declarations and TS names."""
from pathlib import Path
import hashlib
import json
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from jsonschema import Draft202012Validator
from carbentra_iot_contract import CAPABILITIES, PRODUCTS, PRESENCE_GATT, validate_descriptor, validate_event, validate_command
from carbentra_iot_contract.plug_wire import validate_telemetry, validate_ack
for path in (ROOT/'schemas').rglob('*.json'):
    Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
for name in ('plug-event','switch-event','sense-event'):
    validate_event(json.loads((ROOT/'examples'/f'{name}.json').read_text(encoding="utf-8")))
validate_command(json.loads((ROOT/'examples/switch-command.json').read_text(encoding="utf-8")))
for value in json.loads((ROOT/'examples/descriptors.json').read_text(encoding="utf-8")):validate_descriptor(value)
for name,check in [('device-telemetry-v2.json',validate_telemetry),('device-ack-v2.json',validate_ack)]:
    value=json.loads((ROOT/'examples'/name).read_text(encoding="utf-8"));check(value,value['device_id'])
types=(ROOT/'typescript/index.ts').read_text(encoding="utf-8")
union=re.search(r"export type Capability = (.*)",types).group(1)
assert set(re.findall(r"'([^']+)'",union))==set(CAPABILITIES),'TypeScript capability drift'
vector=json.loads((ROOT/'examples/presence-gatt-v1-test-vector.json').read_text(encoding="utf-8"))
assert vector['domain_hex']==PRESENCE_GATT['mac_domain_hex']
assert len(bytes.fromhex(vector['response_hex']))==PRESENCE_GATT['response_bytes']
files=[*ROOT.glob('schemas/**/*.json'),*ROOT.glob('protocols/*.json'),ROOT/'capabilities.json',ROOT/'products.json',*ROOT.glob('python/carbentra_iot_contract/*.py'),ROOT/'typescript/index.ts']
manifest={'application_schema_version':1,'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n', encoding="utf-8", newline='\n')
print('Shared contract schemas, examples, product capabilities, TypeScript names and GATT fixture validated')
