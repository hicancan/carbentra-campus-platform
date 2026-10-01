#!/usr/bin/env python3
"""Freeze reviewed Docker inputs, sharing only unchanged files from a prior immutable snapshot.

No live-source hardlinks, credentials, dependency caches or browser traces are copied.
Run after source owners have frozen. The manifest, not Git HEAD alone, identifies it.
"""
import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = ['.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', '.vite', '.env', '.env.*', '.secrets',
           'secrets', 'runtime', '.runtime', '*.egg-info', 'build', '*.db', '*.db-*', '*.key', '*.pem', '*.p12', '*.pfx', '*.dump', '*.log', '*.tsbuildinfo']
INPUTS = ['backend', 'frontend', 'edge', 'packages/spatial', 'packages/product/dist', 'packages/iot-contract', 'infra', 'tests/system_upgrade']

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit('Output must be a new snapshot directory')
    files = {}
    for name in INPUTS:
        for path in (ROOT / name).rglob('*'):
            relative = path.relative_to(ROOT)
            if any(fnmatch.fnmatch(part, pattern) for part in relative.parts for pattern in BLOCKED): continue
            if relative.parts[0] == 'frontend' and 'dist' in relative.parts: continue
            if relative.parts[:2] == ('edge', 'tests'): continue
            if relative.parts[:2] == ('edge', 'tools') and path.name not in {'status.py', 'migrate_legacy.py'}: continue
            if path.is_symlink(): raise SystemExit(f'Unexpected symlink: {relative}')
            if path.is_file(): files[relative.as_posix()] = digest(path)
    for path in [ROOT / '.dockerignore', ROOT / '.gitattributes', ROOT / 'pyproject.toml', ROOT / 'uv.lock', ROOT / '.python-version', ROOT / 'package.json', ROOT / 'package-lock.json', *ROOT.glob('compose*.yaml')]:
        files[path.relative_to(ROOT).as_posix()] = digest(path)
    args.output.mkdir(parents=True)
    linked = copied = 0
    for name, expected in files.items():
        target = args.output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        prior = args.previous / name if args.previous else None
        if prior and prior.is_file() and not prior.is_symlink() and digest(prior) == expected:
            os.link(prior, target)
            linked += target.stat().st_size
        else:
            shutil.copy2(ROOT / name, target)
            copied += target.stat().st_size
        if digest(target) != expected or digest(ROOT / name) != expected:
            raise SystemExit(f'Source changed during freeze: {name}; discard this incomplete snapshot')
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'base_git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_sha256': dict(sorted(files.items())), 'files': len(files), 'copied_bytes': copied, 'unchanged_prior_snapshot_linked_bytes': linked,
        'note': 'Exact approved filesystem build snapshot; no live-source hardlinks. Git base alone does not identify uncommitted build inputs.'}
    path = args.output / 'source-snapshot.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n', encoding="utf-8")
    print(json.dumps({'path': str(args.output), 'manifest_sha256': digest(path), 'files': len(files), 'copied_bytes': copied, 'linked_bytes': linked}, indent=2))

if __name__ == '__main__': main()
