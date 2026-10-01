"""The evidence gate must notice source additions, modifications and removals."""
from source_snapshot import fingerprint


def test_source_snapshot_ignores_runtime_and_detects_source_changes(tmp_path):
    app=tmp_path/'backend/app';app.mkdir(parents=True)
    source=app/'module.py';source.write_text('value=1\n', encoding="utf-8")
    before=fingerprint(tmp_path)
    runtime=tmp_path/'.runtime';runtime.mkdir();(runtime/'test-secret.txt').write_text('inert local fixture', encoding="utf-8")
    cache=app/'__pycache__';cache.mkdir();(cache/'module.pyc').write_bytes(b'inert')
    assert fingerprint(tmp_path)==before
    source.write_text('value=2\n', encoding="utf-8");assert fingerprint(tmp_path)!=before
    added=app/'added.py';added.write_text('value=3\n', encoding="utf-8")
    assert 'backend/app/added.py' in fingerprint(tmp_path)
    source.unlink();assert 'backend/app/module.py' not in fingerprint(tmp_path)


def test_source_snapshot_includes_migrations_tests_and_harness(tmp_path):
    paths=('backend/alembic/versions/new_revision.py','backend/tests/test_contract.py',
           'tests/acceptance/new_case.py','tools/verify-local.ps1',
           'packages/contracts/openapi.json','packages/spatial/dist/manifest.json')
    for name in paths:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('inert fixture\n', encoding="utf-8")
    assert set(fingerprint(tmp_path))==set(paths)
