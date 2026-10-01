"""Browser-facing JSON must preserve exact counters beyond JavaScript's safe range."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import utcnow
from app.main import create_app
from app.models import Campus, Command, Device
from app.schemas import TelemetryIn
from app.telemetry import ingest_sample


@pytest.fixture
def counter_api(tmp_path):
    app=create_app(Settings(env="test", database_url=f"sqlite:///{tmp_path/'counter.sqlite3'}",
        dev_auth=True, seed_demo=False, worker_enabled=False))
    with TestClient(app, raise_server_exceptions=False) as client:
        with app.state.session_factory() as db:
            db.add(Campus(id="qa-counter-campus", name="Local counter fixture", source="acceptance"))
            db.commit()
        auth=client.post('/api/v1/auth/login', json={"username":"admin", "password":"development-only"})
        assert auth.status_code==200
        headers={"X-CSRF-Token":auth.json()['data']['csrf_token']}
        response=client.post('/api/v1/devices', headers=headers, json={"id":"QA-UINT64", "name":"Local counter fixture",
            "campus_id":"qa-counter-campus", "source_mode":"SIMULATED", "critical":False,
            "allow_control":True, "capabilities":["metering","hold"]})
        assert response.status_code==201, response.text
        response=client.patch('/api/v1/devices/QA-UINT64', headers=headers, json={"commissioned":True})
        assert response.status_code==200, response.text
        with app.state.session_factory() as db:
            now=utcnow()
            ingest_sample(db, TelemetryIn(device_id="QA-UINT64", boot_epoch="a"*32, sample_seq="1", observed_at=now,
                time_source="simulated", time_uncertainty_ms=0.0, active_power_w=100.0, voltage_v=230.0,
                current_a=0.5, energy_import_wh=1.0, energy_export_wh=0.0, desired_on=True, output_present=True,
                fault_latched=False, valid=True, calibrated=True, energy_status="known", source_mode="SIMULATED",
                source_version="qa-uint64-http"))
            db.commit()
        yield app, client, headers


@pytest.mark.parametrize("sequence", [2**31+7, 2**53+7, 2**64-1])
def test_uint64_sequence_is_an_exact_json_string_on_all_command_routes(counter_api, sequence):
    app, client, headers=counter_api
    with app.state.session_factory() as db:
        db.get(Device, "QA-UINT64").next_command_sequence=sequence
        db.commit()
    response=client.post('/api/v1/commands', headers=headers|{"Idempotency-Key":"qa-counter-first"},
        json={"device_id":"QA-UINT64", "action":"hold", "reason":"Local exact-counter fixture", "expires_in_seconds":30})
    assert response.status_code==201, response.text
    command=response.json()['data']
    assert command['sequence']==str(sequence)
    detail=client.get('/api/v1/commands/'+command['id'])
    assert detail.status_code==200 and detail.json()['data']['sequence']==str(sequence)
    listing=client.get('/api/v1/commands', params={"device_id":"QA-UINT64"})
    assert listing.status_code==200
    assert [row['sequence'] for row in listing.json()['data']]==[str(sequence)]
    if sequence==2**64-1:
        with app.state.session_factory() as db:
            saved=db.get(Command, command['id'])
            saved.status="timed_out"
            saved.expires_at=utcnow()-timedelta(seconds=1)
            db.commit()
        exhausted=client.post('/api/v1/commands', headers=headers|{"Idempotency-Key":"qa-counter-exhausted"},
            json={"device_id":"QA-UINT64", "action":"hold", "reason":"Must not wrap sequence", "expires_in_seconds":30})
        assert exhausted.status_code==409, exhausted.text
        assert exhausted.json()['error']['code']=='sequence_exhausted'
