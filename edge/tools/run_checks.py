"""Source-bound Edge checks; release mode requires compiled cross-language gates."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
parser = argparse.ArgumentParser()
parser.add_argument('--release', action='store_true')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.release:
    for name in ('CARBENTRA_STARTUP_TEST_BINARY', 'CARBENTRA_TIME_TEST_BINARY', 'CARBENTRA_CERT_TEST_BINARY'):
        if not Path(os.environ.get(name, '/nonexistent')).is_file():
            raise SystemExit('Required compiled host gate missing: ' + name)

sources = [*ROOT.glob('*.py'), *ROOT.glob('tests/*.py'), *ROOT.glob('tools/*.py'),
           REPO / 'uv.lock', REPO / 'pyproject.toml',
           *(REPO / 'packages/iot-contract').rglob('*.json'),
           *(REPO / 'packages/iot-contract/python').rglob('*.py')]


def fingerprints():
    return {path.relative_to(REPO).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(sources)}


before = fingerprints()
result = subprocess.run([sys.executable, '-m', 'pytest', str(ROOT / 'tests'), '-r', 's', '--tb=short',
                         '-o', f'cache_dir={args.output.parent / "pytest-cache"}'],
                        capture_output=True, text=True, encoding='utf-8')
print(result.stdout, end='')
print(result.stderr, end='', file=sys.stderr)
locked = {package['name']: package['version']
          for package in tomllib.loads((REPO / 'uv.lock').read_text(encoding='utf-8'))['package']}
project = tomllib.loads((REPO / 'pyproject.toml').read_text(encoding='utf-8'))
direct = [re.split(r'[<>=!~; ]', requirement)[0] for requirement in project['dependency-groups']['edge']]
installed = {}
for name in direct:
    try:
        installed[name] = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        installed[name] = None
lock_matches = all(installed[name] == locked.get(name) for name in direct)
all_installed = {re.sub(r'[-_.]+', '-', dist.metadata['Name']).lower(): dist.version
                 for dist in importlib.metadata.distributions()}
version_mismatches = {name: version for name, version in all_installed.items()
                      if locked.get(name) != version}
uv = shutil.which('uv')
dependency_check = subprocess.run([uv, '--no-cache', 'pip', 'check', '--python', sys.executable],
                                 capture_output=True, text=True) if uv else None
runtime_lock_matches = lock_matches and not version_mismatches and dependency_check is not None and dependency_check.returncode == 0
# The inverse OS branch cannot execute on one host. Every other skipped gate,
# including missing compiled C fixtures, keeps release verification unsuccessful.
allowed_skips = ('POSIX private-key permissions are verified in the Linux suite',
                 'Authenticated Sense enrollment uses POSIX private-key permissions') if os.name != 'posix' else ('Non-POSIX startup guard',)
skipped = [line for line in result.stdout.splitlines() if line.startswith('SKIPPED ')]
unexpected_skips = [line for line in skipped if not any(reason in line for reason in allowed_skips)]
record = {
    'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'software host/parser/transport tests; no RF/mains/physical qualification',
    'success': result.returncode == 0 and before == fingerprints()
               and (not args.release or (not unexpected_skips and runtime_lock_matches)),
    'release_gates_required': args.release,
    'direct_dependency_lock_matches': lock_matches,
    'runtime_dependency_lock_matches': runtime_lock_matches,
    'installed_version_mismatches': version_mismatches,
    'dependencies': installed,
    'platform_specific_skips': skipped,
    'unexpected_skips': unexpected_skips,
    'summary': result.stdout.strip().splitlines()[-1] if result.stdout.strip() else '',
    'source_sha256': fingerprints(), 'source_sha256_before': before,
    'changed_during_run': before != fingerprints(),
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
raise SystemExit(0 if record['success'] else 1)
