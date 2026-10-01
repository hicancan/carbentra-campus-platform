from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings
from app.db import utcnow
from app.models import Campus, Building
from app.registry import create_device
from app.telemetry import ingest_sample
from app.schemas import TelemetryIn


@pytest.fixture
def app(tmp_path):
    application = create_app(Settings(env="test", database_url=f"sqlite:///{tmp_path/'test.db'}", dev_auth=True, worker_enabled=False,
        adapter_token="unit-test-fixture-token-not-real-secret-123", adapter_allowed_device_ids=["SIM-A", "SIM-VIRTUAL"]))
    with TestClient(application, raise_server_exceptions=True) as client:
        with application.state.session_factory() as db:
            for name in ("A", "B"):
                db.add(Campus(id=name, name=name, source="synthetic_test_fixture"))
            db.flush()
            for name in ("A", "B"):
                db.add(Building(id=f"building-{name}", campus_id=name, name=name, source="synthetic_test_fixture"))
            db.flush()
            for ident in ("SIM-A", "SIM-VIRTUAL"):
                device = create_device(db, dict(id=ident, name=ident, campus_id="A", building_id="building-A", kind="smart_plug", source_mode="SIMULATED", critical=False,
                    allow_control=True, capabilities=["metering", "hold", "shed", "restore"]), "test")
                device.commissioned = True
                device.dispatch_mode = "VIRTUAL" if ident == "SIM-VIRTUAL" else "IN_PROCESS"
                db.flush()
                now = utcnow()
                ingest_sample(db, TelemetryIn(device_id=ident, boot_epoch="a"*32, sample_seq="1", observed_at=now, time_source="simulated", time_uncertainty_ms=0.0,
                    active_power_w=500.0, voltage_v=230.0, current_a=2.2, energy_import_wh=0.0, energy_export_wh=0.0, desired_on=True, output_present=True, fault_latched=False,
                    valid=True, calibrated=True, energy_status="known", source_mode="SIMULATED", source_version="unit-test"))
            db.commit()
        yield application, client


@pytest.fixture
def admin(app):
    _, client = app
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "development-only"})
    return client, {"X-CSRF-Token": response.json()["data"]["csrf_token"]}
