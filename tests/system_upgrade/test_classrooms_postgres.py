"""Run the canonical classroom behavior tests against an actually migrated PostgreSQL clone.

The imported tests retain their original assertions; this module changes only their
persistence fixture. Run with tools/verify-local.ps1, never production.
"""
import importlib.util
import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

ROOT = Path(__file__).resolve().parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

canonical = load('classroom_upgrade_canonical', ROOT / 'backend/tests/test_classrooms.py')
fixtures = load('classroom_upgrade_fixtures', ROOT / 'backend/tests/conftest.py')
for name in dir(canonical):
    if name.startswith('test_') or name == 'room_app':
        globals()[name] = getattr(canonical, name)
admin = fixtures.admin
URL = os.environ.get('SYSTEM_UPGRADE_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not URL, reason='requires disposable migrated PostgreSQL fixture')

@pytest.fixture
def app(tmp_path, monkeypatch):
    parsed = urlparse(URL.replace('postgresql+psycopg://', 'postgresql://'))
    if parsed.hostname not in {'localhost', '127.0.0.1'} or parsed.username != 'qa' or parsed.password or parsed.path != '/acceptance_upgrade':
        raise RuntimeError('Only the disposable loopback qa/acceptance_upgrade template is permitted')
    name = 'acceptance_upgrade_' + uuid4().hex
    connection = psycopg.connect(host=parsed.hostname, port=parsed.port, user='qa', dbname='postgres', autocommit=True)
    connection.execute(sql.SQL('CREATE DATABASE {} TEMPLATE acceptance_upgrade').format(sql.Identifier(name)))
    settings_type = fixtures.Settings
    def migrated_settings(**kwargs):
        kwargs['database_url'] = URL.rsplit('/', 1)[0] + '/' + name
        kwargs['auto_migrate'] = False
        return settings_type(**kwargs)
    monkeypatch.setattr(fixtures, 'Settings', migrated_settings)
    if os.environ.get('SYSTEM_UPGRADE_DEBUG_HASH') == '1':
        import json
        from app import classrooms
        original_hash = classrooms.payload_hash
        def record_hash(value):
            result = original_hash(value)
            if isinstance(value, dict) and value.get('channel_id') == 'channel-plug':
                print('CHANNEL_HASH_FIXTURE ' + json.dumps({'value': value, 'hash': result}, default=str, sort_keys=True))
            return result
        monkeypatch.setattr(classrooms, 'payload_hash', record_hash)
    try:
        yield from fixtures.app.__wrapped__(tmp_path)
    finally:
        connection.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
        connection.close()
