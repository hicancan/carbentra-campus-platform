"""The container probe imports stdlib only and checks durable tick/process identity."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import pytest
from app import worker_health as health


def test_current_process_heartbeat_and_stale_tick(tmp_path):
    health.publish('control',time.time(),tmp_path)
    assert health.healthy(directory=tmp_path)
    health.publish('control',time.time()-11,tmp_path)
    assert not health.healthy(directory=tmp_path)
    health.publish('control',time.time()+60,tmp_path)
    assert not health.healthy(directory=tmp_path)


def test_previous_process_identity_is_not_a_healthy_restart(tmp_path):
    health.publish('control',time.time(),tmp_path)
    path=tmp_path/'control.json';value=json.loads(path.read_text(encoding="utf-8"))
    value['process_start']='not-this-process';path.write_text(json.dumps(value), encoding="utf-8")
    assert not health.healthy(directory=tmp_path)
    value['pid']=2**31;path.write_text(json.dumps(value), encoding="utf-8")
    assert not health.healthy(directory=tmp_path)


@pytest.mark.parametrize('content',['{','null','[]','x'*4097])
def test_malformed_or_excessive_heartbeat_fails_closed(tmp_path,content):
    (tmp_path/'control.json').write_text(content, encoding="utf-8")
    assert not health.healthy(directory=tmp_path)


def test_cli_uses_no_application_or_database_dependencies(tmp_path):
    health.publish('control',time.time(),tmp_path)
    env={**os.environ,'CARBENTRA_WORKER_HEALTH_DIR':str(tmp_path)}
    run=subprocess.run([sys.executable,'-m','app.worker_health'],env=env,capture_output=True)
    assert run.returncode==0,run.stderr
    probe="import sys, app.worker_health; assert not any(x in sys.modules for x in ('sqlalchemy','pydantic','fastapi','app.control','app.models'))"
    run=subprocess.run([sys.executable,'-c',probe],env=env,capture_output=True)
    assert run.returncode==0,run.stderr


def test_heartbeat_published_only_after_successful_tick(app,tmp_path,monkeypatch):
    import threading
    from app.worker import role_loop
    from app.models import State
    application,_=app;stop=threading.Event();original=health.publish
    def once(role,epoch):
        with application.state.session_factory() as db:
            assert db.get(State,'worker').value['last_tick_epoch']==epoch
        original(role,epoch,tmp_path);stop.set()
    monkeypatch.setattr(health,'publish',once)
    role_loop(application.state.session_factory,application.state.settings,stop,'control')
    assert health.healthy(directory=tmp_path)
