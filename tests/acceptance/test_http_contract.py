"""Black-box HTTP acceptance with explicit synthetic fixtures and disposable DB."""
import json
import os
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.db import utcnow
from app.main import create_app
from app.models import Report

PREFIX = "/api/v1"
QA_ADAPTER_TOKEN = "local-acceptance-only-not-a-real-secret-000000"
QA_IDS = ["QA-HTTP-SIM", "QA-HTTP-REAL", "QA-HTTP-REPLAY"]


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    path = tmp_path_factory.mktemp("campus-http") / "test.sqlite3"
    settings = Settings(env="test", database_url=os.environ.get("ACCEPTANCE_DATABASE_URL", f"sqlite:///{path}"), dev_auth=True, seed_demo=True, simulation_enabled=False, worker_enabled=False, adapter_token=QA_ADAPTER_TOKEN, adapter_allowed_device_ids=QA_IDS)
    application = create_app(settings)
    with TestClient(application, raise_server_exceptions=False) as client:
        yield application, client


def login(client, role="admin"):
    response = client.post(PREFIX+"/auth/login", json={"username": role, "password": "development-only"})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["data"]["csrf_token"]}


@pytest.fixture
def admin(app):
    _, client = app
    headers = login(client)
    return client, headers


def data(response, status=200):
    assert response.status_code == status, response.text
    body = response.json()
    assert "data" in body
    return body["data"]


def fail(response, status, code=None):
    assert response.status_code == status, response.text
    body = response.json()
    assert body["error"]["request_id"]
    if code:
        assert body["error"]["code"] == code
    return body["error"]


@pytest.fixture(scope="module")
def qa_devices(app):
    _, client = app
    headers = login(client)
    campus = data(client.get(PREFIX+"/campuses"))[0]
    building = data(client.get(PREFIX+"/buildings", params={"campus_id": campus["id"]}))[0]
    rows = []
    for ident, mode in zip(QA_IDS, ["SIMULATED", "REAL", "REPLAYED"]):
        rows.append(data(client.post(PREFIX+"/devices", headers=headers, json={"id": ident, "name": "Independent QA fixture", "campus_id": campus["id"], "building_id": building["id"], "kind": "smart_plug", "source_mode": mode, "critical": False, "allow_control": mode=="SIMULATED", "capabilities": ["metering", "shed", "restore", "hold"]}), 201))
    return rows


def measurement(ident=QA_IDS[0], seq="1", **changes):
    now = utcnow().isoformat()
    values = dict(device_id=ident, boot_epoch="qa-http-epoch", sample_seq=seq, observed_at=now, time_source="simulated", time_uncertainty_ms=0.0, active_power_w=360.0, voltage_v=230.0, current_a=1.6, energy_import_wh=1000.0, energy_export_wh=0.0, desired_on=True, output_present=True, fault_latched=False, valid=True, calibrated=True, energy_status="known", energy_uncertain_intervals=0, source_mode="SIMULATED", source_version="qa-http-v1")
    values.update(changes)
    return values


def test_full_campus_seed_is_reference_plus_explicit_simulation(admin):
    client, _ = admin
    assert len(data(client.get(PREFIX+"/campuses"))) == 3
    buildings = client.get(PREFIX+"/buildings", params={"limit": 500}).json()
    assert buildings["meta"]["total"] == 136
    assert len(buildings["data"]) == 136
    spaces = client.get(PREFIX+"/spaces", params={"limit": 500}).json()
    assert spaces["meta"]["total"] == 603
    assert len(spaces["data"]) == 500
    remainder = client.get(PREFIX+"/spaces", params={"limit": 500, "offset": 500}).json()
    assert len(remainder["data"]) == 103
    devices = client.get(PREFIX+"/devices", params={"limit": 500}).json()
    assert devices["meta"]["total"] >= 680
    assert all(d["source_mode"]=="SIMULATED" and not d["provenance"].get("real_installation_claim") for d in devices["data"])


def test_unauthenticated_login_csrf_origin_and_logout(app):
    application, _ = app
    with TestClient(application, raise_server_exceptions=False) as client:
        fail(client.get(PREFIX+"/devices"), 401)
        headers = login(client)
        cookie = client.cookies.get("carbentra_session")
        assert cookie
        fail(client.patch(PREFIX+"/settings", json={"stale_after_seconds": 100}), 403, "csrf_failed")
        fail(client.patch(PREFIX+"/settings", headers={"X-CSRF-Token":"invalid"}, json={"stale_after_seconds": 100}), 403)
        fail(client.patch(PREFIX+"/settings", headers=headers|{"Origin":"https://attacker.invalid"}, json={"stale_after_seconds": 100}), 403, "origin_denied")
        assert data(client.post(PREFIX+"/auth/logout", headers=headers))["logged_out"]
        client.cookies.set("carbentra_session", cookie)
        fail(client.get(PREFIX+"/auth/me"), 401)


@pytest.mark.parametrize("role,path,payload", [
    ("viewer", "/devices", {}),
    ("viewer", "/commands", {}),
    ("analyst", "/commands", {}),
    ("operator", "/reports", {}),
])
def test_role_denial_precedes_resource_mutation(app, role, path, payload):
    _, client = app
    headers = login(client, role)
    response = client.post(PREFIX+path, headers=headers, json=payload)
    fail(response, 403, "forbidden")


def test_cookie_and_security_headers(app):
    _, client = app
    response = client.post(PREFIX+"/auth/login", json={"username":"admin", "password":"development-only"})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]


def test_invalid_and_oversized_json_is_rejected_without_echo(admin):
    client, headers = admin
    fail(client.post(PREFIX+"/devices", headers=headers|{"Content-Type":"application/json"}, content=b'{"secret_marker":'), 422)
    fail(client.post(PREFIX+"/devices", headers=headers|{"Content-Type":"application/json"}, content=b'"'+b"x"*(2*1024*1024)+b'"'), 413)
    response = client.post(PREFIX+"/auth/login", json={"username":"admin", "password":"secret-marker"*100})
    fail(response, 422)
    assert "secret-marker" not in response.text


def test_bounded_pagination_and_unknown_resources(admin):
    client, _ = admin
    for query in ({"limit":0}, {"limit":501}, {"offset":-1}):
        fail(client.get(PREFIX+"/devices", params=query), 422)
    fail(client.get(PREFIX+"/devices/QA-MISSING-DEVICE"), 404)


def test_ingestion_auth_scope_and_nonfinite_values(admin, qa_devices):
    client, _ = admin
    body = {"samples":[measurement()]}
    fail(client.post(PREFIX+"/ingest/telemetry", json=body), 401, "adapter_unauthorized")
    auth = {"Authorization":f"Bearer {QA_ADAPTER_TOKEN}"}
    fail(client.post(PREFIX+"/ingest/telemetry", headers=auth, json={"samples":[measurement("QA-NOT-ALLOWED")]}), 403, "adapter_scope_denied")
    for value in [float("nan"), float("inf"), -float("inf")]:
        raw = json.dumps({"samples":[measurement(active_power_w=value)]})
        fail(client.post(PREFIX+"/ingest/telemetry", headers=auth|{"Content-Type":"application/json"}, content=raw), 422)
    fail(client.post(PREFIX+"/ingest/telemetry", headers=auth, json={"samples":[measurement(valid="true")]}), 422)


def test_http_telemetry_dedup_conflict_and_mode_mismatch(admin, qa_devices):
    client, _ = admin
    auth = {"Authorization":f"Bearer {QA_ADAPTER_TOKEN}"}
    value = measurement(seq="100")
    first = data(client.post(PREFIX+"/ingest/telemetry", headers=auth, json={"samples":[value]}))
    again = data(client.post(PREFIX+"/ingest/telemetry", headers=auth, json={"samples":[value]}))
    assert first["durable"] and first["stored"] == 1 and again["duplicates"] == 1
    fail(client.post(PREFIX+"/ingest/telemetry", headers=auth, json={"samples":[value|{"energy_import_wh":2000.0}]}), 409, "telemetry_conflict")
    fail(client.post(PREFIX+"/ingest/telemetry", headers=auth, json={"samples":[measurement(QA_IDS[1], seq="101")]}), 409, "source_mode_mismatch")


def test_firmware_validation_errors_are_client_errors(admin, qa_devices):
    client, _ = admin
    auth = {"Authorization":f"Bearer {QA_ADAPTER_TOKEN}"}
    raw = dict(schema_version=2, device_id=QA_IDS[1], boot_epoch="qa-wire-epoch", sample_seq="1", monotonic_ms=1000, time_quality="unknown", valid=True, calibrated=True, active_w="not-a-number", voltage_v=230.0, current_a=1.0, known_forward_wh_since_boot=10.0, known_reverse_wh_since_boot=0.0, energy_status="known")
    response = client.post(PREFIX+"/ingest/firmware", headers=auth, json=raw)
    fail(response, 422)


def test_real_replayed_actuation_and_commissioning_are_disabled(admin, qa_devices):
    client, headers = admin
    for ident in QA_IDS[1:]:
        fail(client.patch(PREFIX+f"/devices/{ident}", headers=headers, json={"commissioned":True}), 409, "physical_control_disabled")
        fail(client.post(PREFIX+"/commands", headers=headers|{"Idempotency-Key":uuid4().hex}, json={"device_id":ident, "action":"shed", "reason":"Local QA forbidden actuation"}), 409, "physical_control_disabled")
    status = data(client.get(PREFIX+"/system/status"))
    assert status["physical_control"]["enabled"] is False


def test_alarm_notes_and_lifecycle_are_persisted(admin):
    client, headers = admin
    alarm = data(client.get(PREFIX+"/alarms", params={"status":"open"}))[0]
    base = PREFIX+f"/alarms/{alarm['id']}"
    fail(client.post(base+"/resolve", headers=headers, json={"note":"QA premature resolution"}), 409)
    ack = data(client.post(base+"/acknowledge", headers=headers, json={"note":"QA acknowledged simulation"}))
    assert ack["status"] == "acknowledged"
    data(client.post(base+"/notes", headers=headers, json={"note":"QA checked evidence"}))
    result = data(client.post(base+"/resolve", headers=headers, json={"note":"QA resolved simulated fixture"}))
    assert result["status"] == "resolved" and len(result["notes"]) == 3
    assert data(client.get(base))["notes"] == result["notes"]
    fail(client.post(base+"/acknowledge", headers=headers, json={}), 409)


def test_binding_clears_control_and_preserves_history(admin, qa_devices):
    client, headers = admin
    ident = QA_IDS[0]
    old = data(client.get(PREFIX+f"/devices/{ident}"))
    campus_buildings = data(client.get(PREFIX+"/buildings", params={"campus_id":old["campus_id"]}))
    target = next(x for x in campus_buildings if x["id"] != old["building_id"])
    data(client.patch(PREFIX+f"/devices/{ident}", headers=headers, json={"commissioned":True}))
    moved = data(client.put(PREFIX+f"/devices/{ident}/binding", headers=headers, json={"campus_id":target["campus_id"], "building_id":target["id"], "reason":"QA synthetic relocation"}))
    assert not moved["commissioned"] and not moved["allow_control"]
    history = data(client.get(PREFIX+f"/devices/{ident}"))["binding_history"]
    assert len(history)==2 and history[0]["valid_to"] is None and history[1]["valid_to"] is not None


def test_reports_snapshot_exports_and_secret_redaction(app, admin):
    application, _ = app
    client, headers = admin
    report = data(client.post(PREFIX+"/reports", headers=headers, json={"name":"QA durable energy snapshot", "type":"energy"}), 201)
    report_id = report["id"]
    assert data(client.get(PREFIX+f"/reports/{report_id}"))["content"] == report["content"]
    # Synthetic corruption-like export fixture tests serialization, without touching product rows.
    with application.state.session_factory() as db:
        row = db.get(Report, report_id)
        row.summary = {"operator_text":"=HYPERLINK(\"https://example.invalid\")", "negative":"-1+1", "plain":"safe"}
        db.commit()
    csv = client.get(PREFIX+f"/reports/{report_id}/export", params={"format":"csv"})
    assert csv.status_code == 200 and "attachment" in csv.headers["content-disposition"]
    assert "'=HYPERLINK" in csv.text and "'-1+1" in csv.text
    for path in ("/settings", "/system/status", "/audit"):
        response = client.get(PREFIX+path)
        assert response.status_code == 200
        assert QA_ADAPTER_TOKEN not in response.text
        for field in ('"password_hash"', '"csrf_token"', '"token_hash"', '"database_url"'):
            assert field not in response.text


def test_duplicate_json_object_keys_are_rejected(app):
    _, client = app
    response = client.post(PREFIX+"/auth/login", headers={"Content-Type":"application/json"}, content='{"username":"viewer","username":"admin","password":"development-only"}')
    fail(response, 422)
