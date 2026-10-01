#!/usr/bin/env python3
"""Export/check the live route contracts without database startup or demo seeding."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.config import Settings
from app.main import create_app


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    app=create_app(Settings(env='test',database_url='sqlite:///:memory:',dev_auth=False,worker_enabled=False,auto_migrate=False,seed_demo=False))
    data=(json.dumps(app.openapi(),ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()
    path=ROOT/'packages/contracts/openapi.json'
    if args.check:
        if not path.is_file() or path.read_bytes()!=data:
            raise SystemExit('OpenAPI artifact differs from runtime route contracts; regenerate with backend/tools/export_openapi.py')
    else:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    print(f'{hashlib.sha256(data).hexdigest()}  packages/contracts/openapi.json')


if __name__=='__main__':
    main()
