"""Fetch only content-addressed, manifest-verified public semantic JSON.

No restricted originals or SVG images are downloaded. A changed upstream pointer
never silently changes the requested snapshot. Existing matching files are reused.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request

BASE = 'https://njupt.hicancan.top/generated/space'
PIN = 'c6a20dc3cca30daa6fdd813ae08d881f782e7e3d3e3eda03f402f556ad17222f'

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()

def references(manifest):
    return [ref for group in manifest['artifacts'].values() for ref in (group if isinstance(group, list) else [group])]

def verify_manifest(manifest, expected):
    if manifest['format'] == 'njupt-space-metadata-snapshot':
        if (manifest.get('source_snapshot_id') != expected
                or manifest.get('geometry_publication') != 'metadata_only'
                or manifest.get('geometry_unit_count') != 0):
            raise ValueError('Unexpected metadata projection provenance')
    elif manifest['format'] != 'njupt-space-snapshot' or manifest['snapshot_id'] != expected:
        raise ValueError('Unexpected search snapshot identity')
    if hashlib.sha256(canonical({k:v for k,v in manifest.items() if k != 'snapshot_id'})).hexdigest() != manifest['snapshot_id']:
        raise ValueError('Search manifest content hash mismatch')

def fetch(root, expected=PIN):
    root.mkdir(parents=True, exist_ok=True)
    pointer = root/'manifest.json'
    raw = pointer.read_bytes() if pointer.exists() else urllib.request.urlopen(f'{BASE}/manifest.json', timeout=60).read()
    manifest = json.loads(raw)
    verify_manifest(manifest, expected)
    def one(ref):
        rel = PurePosixPath(ref['path'])
        if rel.is_absolute() or '..' in rel.parts or len(rel.parts) != 1 or rel.suffix != '.json':
            raise ValueError(f'Unsafe semantic artifact path: {rel}')
        path = root/str(rel)
        data = path.read_bytes() if path.exists() else urllib.request.urlopen(f'{BASE}/{expected}/{rel}', timeout=60).read()
        if len(data) != ref['bytes'] or hashlib.sha256(data).hexdigest() != ref['sha256']:
            raise ValueError(f'Artifact hash/size mismatch: {rel}')
        if json.loads(data).get('source_id') != manifest['source_id']:
            raise ValueError(f'Artifact source identity mismatch: {rel}')
        if not path.exists(): path.write_bytes(data)
        return str(rel)
    with ThreadPoolExecutor(max_workers=6) as pool:
        paths = list(pool.map(one, references(manifest)))
    if not pointer.exists(): pointer.write_bytes(raw)
    return {'snapshot_id': expected, 'verified_artifacts':len(paths)}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--snapshot-id', default=PIN)
    args=p.parse_args()
    print(json.dumps(fetch(args.output, args.snapshot_id)))
