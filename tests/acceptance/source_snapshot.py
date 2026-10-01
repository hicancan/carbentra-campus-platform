#!/usr/bin/env python3
"""Hash test inputs, including added/deleted files, without secrets or runtime data."""
import argparse
import hashlib
import json
from pathlib import Path


def fingerprint(root):
    root=Path(root).resolve()
    paths=set()
    for directory in ('backend/app','backend/alembic','backend/tests','tests/acceptance','tools'):
        paths.update(path for path in (root/directory).rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.suffix in {'.py','.mjs','.ps1','.json','.ini'})
    for name in ('uv.lock','pyproject.toml','backend/pyproject.toml','backend/alembic.ini',
                 'packages/spatial/dist/manifest.json','packages/spatial/dist/seed.json',
                 'packages/contracts/openapi.json'):
        path=root/name
        if path.is_file():paths.add(path)
    result={}
    for path in sorted(paths):
        digest=hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
        result[path.relative_to(root).as_posix()]=digest.hexdigest()
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--compare',type=Path)
    args=parser.parse_args();current=fingerprint(args.root)
    args.output.write_text(json.dumps(current,indent=2)+'\n', encoding="utf-8")
    if args.compare:
        before=json.loads(args.compare.read_text(encoding="utf-8"))
        changed=sorted(key for key in set(before)|set(current) if before.get(key)!=current.get(key))
        print(json.dumps({'source_snapshot_stable':not changed,'changed_during_run':changed}))
        return bool(changed)
    print(json.dumps({'source_snapshot_files':len(current)}))
    return False


if __name__=='__main__':raise SystemExit(main())
