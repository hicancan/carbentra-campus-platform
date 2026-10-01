"""Production-mode reference-only CLI on a private disposable PostgreSQL schema."""
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db import make_engine

ROOT=Path(__file__).resolve().parents[2]
URL=os.environ.get('ACCEPTANCE_DATABASE_URL','')
pytestmark=pytest.mark.skipif(not URL.startswith('postgresql'), reason='Requires disposable PostgreSQL acceptance fixture')


def test_production_reference_cli_migrates_checks_applies_and_preserves_empty_operations():
    parsed=urlparse(URL.replace('postgresql+psycopg://','postgresql://'))
    if parsed.hostname not in {'127.0.0.1','localhost'} or parsed.username!='qa' or parsed.password or not parsed.path.lstrip('/').startswith('acceptance'):
        raise RuntimeError('Reference CLI test requires the disposable loopback qa/acceptance fixture')
    engine=make_engine(URL)
    schema='acceptance_reference_'+uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url=make_url(URL).update_query_dict({'options':'-csearch_path='+schema}).render_as_string(hide_password=False)
    scoped=make_engine(scoped_url)
    env=os.environ|{
        'PYTHONPATH':str(ROOT/'backend'), 'CARBENTRA_ENV':'production', 'CARBENTRA_DATABASE_URL':scoped_url,
        'CARBENTRA_DEV_AUTH':'false', 'CARBENTRA_SEED_DEMO':'false', 'CARBENTRA_SIMULATION_ENABLED':'false',
        'CARBENTRA_WORKER_ENABLED':'false', 'CARBENTRA_AUTO_MIGRATE':'false', 'CARBENTRA_COOKIE_SECURE':'true',
        'CARBENTRA_ALLOWED_ORIGINS':'["https://localhost"]', 'CARBENTRA_PHYSICAL_DISPATCH_ENABLED':'false',
        'CARBENTRA_PHYSICAL_RELEASE_IDS':'[]',
        'CARBENTRA_SPATIAL_SEED_PATH':str(ROOT/'packages/spatial/dist/seed.json'),
        'CARBENTRA_SPATIAL_MANIFEST_PATH':str(ROOT/'packages/spatial/dist/manifest.json'),
    }
    for secret in ('CARBENTRA_ADMIN_PASSWORD','CARBENTRA_ADAPTER_TOKEN'):
        env.pop(secret,None)
    def run(module,*args,expected=0):
        result=subprocess.run([sys.executable,'-m',module,*args],cwd=ROOT/'backend',env=env,capture_output=True,text=True,timeout=60)
        assert result.returncode==expected,result.stdout+result.stderr
        return json.loads(result.stdout) if module=='app.import_spatial' else result
    def counts():
        names=('campuses','buildings','floors','spaces','users','devices','device_bindings','telemetry','commands','carbon_factors','tariffs','audit_log')
        with scoped.connect() as connection:
            return {name:connection.scalar(text(f'SELECT count(*) FROM {name}')) for name in names}
    try:
        run('app.migrate')
        baseline=counts()
        assert not any(baseline.values())
        pin=json.loads((ROOT/'packages/spatial/dist/manifest.json').read_text(encoding="utf-8"))['version']
        report=run('app.import_spatial','--check','--expected-version',pin)
        assert report['reference_only'] is True and report['applicable'] is True
        assert len(report['resources']['buildings']['additions'])==136
        assert counts()==baseline, 'Read-only plan must not seed even reference rows'
        rejected=run('app.import_spatial','--apply','--expected-version','0'*64,expected=2)
        assert rejected['error']['code']=='spatial_package_invalid' and counts()==baseline
        applied=run('app.import_spatial','--apply','--expected-version',pin)
        assert applied['applied'] is True and applied['changed'] is True
        after=counts()
        assert {key:after[key] for key in ('campuses','buildings','floors','spaces')}=={'campuses':3,'buildings':136,'floors':41,'spaces':603}
        assert all(after[key]==0 for key in ('users','devices','device_bindings','telemetry','commands','carbon_factors','tariffs'))
        assert after['audit_log']>0
        assert run('app.import_spatial','--apply','--expected-version',pin)['changed'] is False
        assert counts()==after, 'Idempotent reference apply must not rewrite audit or operational state'
    finally:
        scoped.dispose()
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
