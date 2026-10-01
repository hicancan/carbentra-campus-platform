from datetime import timedelta
import pytest
from sqlalchemy import select, text
from app.db import utcnow
from app.models import Audit, Command, Device, Telemetry, SimulatedOutput, User, Report
from app.control import advance_commands
from app.security import password_hash

P = "/api/v1"
TOKEN = "Bearer unit-test-fixture-token-not-real-secret-123"


def assert_ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json()["data"]


def test_adapter_lease_delivery_observation_and_idempotency(app, admin):
    application, _ = app
    client, headers = admin
    command = assert_ok(client.post(P+"/commands", headers=headers|{"Idempotency-Key": "virtual-command-test"}, json={"device_id": "SIM-VIRTUAL", "action": "shed", "reason": "Authorized virtual test"}), 201)
    auth = {"Authorization": TOKEN}
    item = assert_ok(client.get(P+"/adapter/commands", headers=auth))[0]
    assert item["dispatch_mode"] == "VIRTUAL" and item["source_mode"] == "SIMULATED"
    assert item["wire"]["seq"] == "1"
    assert assert_ok(client.get(P+"/adapter/commands", headers=auth)) == []
    delivery = {"lease_id": item["lease_id"], "status": "published"}
    assert assert_ok(client.post(P+f"/adapter/commands/{command['id']}/delivery", headers=auth, json=delivery))["status"] == "dispatched"
    assert assert_ok(client.get(P+f"/commands/{command['id']}"))["result"] is None
    raw = {"schema_version": 2, "device_id": "SIM-VIRTUAL", "boot_epoch": "a"*32, "id": command["id"], "seq": "1", "status": "OBSERVED_VERIFIED", "terminal": True,
        "desired_on": False, "fault_latched": False, "voltage_absence_proven": False, "requested_monotonic_ms": 1000, "deadline_monotonic_ms": 6000,
        "observed_monotonic_ms": 2000, "feedback_valid": True, "output_present": False, "output_sensing": "NO_AC_PULSES_DETECTED"}
    first = assert_ok(client.post(P+"/ingest/ack", headers=auth, json=raw))
    assert first["matched"] and first["durable"]
    assert assert_ok(client.post(P+"/ingest/ack", headers=auth, json=raw))["status"] == "duplicate"
    bad = client.post(P+"/ingest/ack", headers=auth, json=raw|{"observed_monotonic_ms": 2100})
    assert bad.status_code == 409
    final = assert_ok(client.get(P+f"/commands/{command['id']}"))
    assert final["status"] == "verified" and final["result"]["voltage_absence_proven"] is False


@pytest.mark.parametrize("scenario,expected", [("success", "verified"), ("reject", "rejected"), ("fail", "failed"), ("timeout", "timed_out")])
def test_simulator_persists_independent_output_feedback(app, admin, scenario, expected):
    application, _ = app
    client, headers = admin
    command = assert_ok(client.post(P+"/commands", headers=headers|{"Idempotency-Key": "simulation-test-key"}, json={"device_id": "SIM-A", "action": "shed", "reason": "Stateful fixture", "simulation_scenario": scenario, "expires_in_seconds": 10}), 201)
    now = utcnow()
    for seconds in (1, 2, 3, 11):
        with application.state.session_factory() as db:
            advance_commands(db, now+timedelta(seconds=seconds))
            db.commit()
    result = assert_ok(client.get(P+f"/commands/{command['id']}"))
    assert result["status"] == expected
    if expected == "verified":
        with application.state.session_factory() as db:
            sample = db.get(Telemetry, result["history"][-1]["evidence"]["telemetry_id"])
            assert sample.raw_payload["command_id"] == command["id"]
            assert sample.raw_payload["command_sequence"] == "1"
            assert sample.active_power_w == 0
            assert not db.get(SimulatedOutput, "SIM-A").output_present


def test_scoped_role_cannot_read_or_export_other_campus(app, admin):
    application, _ = app
    client, headers = admin
    user = assert_ok(client.post(P+"/users", headers=headers, json={"username": "campus-b-viewer", "display_name": "B viewer", "role": "viewer", "campus_ids": ["B"], "password": "test-provided-password-for-viewer"}), 201)
    report = assert_ok(client.post(P+"/reports", headers=headers, json={"name": "A snapshot", "type": "operations", "campus_id": "A"}), 201)
    assert_ok(client.post(P+"/auth/logout", headers=headers))
    assert_ok(client.post(P+"/auth/login", json={"username": "campus-b-viewer", "password": "test-provided-password-for-viewer"}))
    assert [c["id"] for c in assert_ok(client.get(P+"/campuses"))] == ["B"]
    assert assert_ok(client.get(P+"/devices")) == []
    assert client.get(P+"/devices/SIM-A").status_code == 404
    assert client.get(P+f"/reports/{report['id']}/export").status_code == 404
    assert assert_ok(client.get(P+"/energy/summary", params={"campus_id": "A"}))["known_kwh"] is None


def test_user_role_scope_change_revokes_sessions(app, admin):
    application, _ = app
    client, headers = admin
    target = assert_ok(client.post(P+"/users", headers=headers, json={"username": "operator-a", "display_name": "A operator", "role": "operator", "campus_ids": ["A"], "password": "test-provided-password-for-operator"}), 201)
    from fastapi.testclient import TestClient
    with TestClient(application) as second:
        assert_ok(second.post(P+"/auth/login", json={"username": "operator-a", "password": "test-provided-password-for-operator"}))
        assert_ok(client.patch(P+f"/users/{target['id']}", headers=headers, json={"campus_ids": ["B"]}))
        assert second.get(P+"/auth/me").status_code == 401


def test_schedule_plans_never_claim_observed_occupancy(app, admin):
    client, headers = admin
    now = utcnow()
    event = assert_ok(client.post(P+"/schedules", headers=headers, json={"campus_id": "A", "building_id": "building-A", "title": "Maintenance fixture", "kind": "maintenance", "starts_at": (now-timedelta(minutes=1)).isoformat(), "ends_at": (now+timedelta(hours=1)).isoformat(), "planned_occupancy": 0, "source": "unit test", "source_mode": "SIMULATED"}), 201)
    assert event["observed_occupancy"] == "unknown" and event["control_authorization"] is False
    response = client.post(P+"/commands", headers=headers|{"Idempotency-Key": "maintenance-fixture"}, json={"device_id": "SIM-A", "action": "shed", "reason": "Must be blocked"})
    assert response.status_code == 409 and response.json()["error"]["code"] == "maintenance_interlock"
    assert assert_ok(client.post(P+f"/schedules/{event['id']}/cancel", headers=headers, json={"note": "Maintenance ended"}))["status"] == "cancelled"
    assert client.post(P+"/commands", headers=headers|{"Idempotency-Key": "post-maintenance"}, json={"device_id": "SIM-A", "action": "shed", "reason": "Explicit authorized request"}).status_code == 201


def test_topology_cycle_and_cross_campus_rejected(admin):
    client, headers = admin
    for ident, parent in [("c1", None), ("c2", "c1")]:
        assert_ok(client.post(P+"/circuits", headers=headers, json={"id": ident, "campus_id": "A", "building_id": "building-A", "name": ident, "parent_id": parent}), 201)
    response = client.patch(P+"/circuits/c1", headers=headers, json={"parent_id": "c2"})
    assert response.status_code == 409 and response.json()["error"]["code"] == "topology_cycle"
    response = client.post(P+"/circuits", headers=headers, json={"id": "c3", "campus_id": "B", "building_id": "building-B", "name": "bad", "parent_id": "c1"})
    assert response.status_code == 409


def test_audit_database_is_append_only(app, admin):
    application, _ = app
    with application.state.session_factory() as db:
        row = db.scalar(select(Audit).limit(1))
        assert row is not None
        with pytest.raises(Exception, match="append-only"):
            db.execute(text("UPDATE audit_log SET action='tampered' WHERE id=:id"), {"id": row.id})
        db.rollback()


def test_orphaned_command_issuer_cannot_be_leased_or_dispatched(app,admin):
    from app.models import Command
    from app.adapter import poll_commands
    from app.control import advance_commands
    from app.db import utcnow
    application,_=app;client,headers=admin
    for device_id in ('SIM-A','SIM-VIRTUAL'):
        response=client.post('/api/v1/commands',headers=headers|{'Idempotency-Key':'orphan-issuer-'+device_id},json={'device_id':device_id,'action':'hold','reason':'Inert orphan-issuer regression'})
        assert response.status_code==201,response.text
        with application.state.session_factory() as db:
            command=db.get(Command,response.json()['data']['id']);command.created_by='deleted-principal-fixture';db.commit()
            if device_id=='SIM-VIRTUAL':
                assert poll_commands(db,application.state.settings,[device_id])==[]
            else:
                advance_commands(db,settings=application.state.settings)
            db.commit()
            assert command.status=='rejected'


def test_strategy_known_zero_is_not_unknown_and_missing_boundary_is_explicit(app,admin):
    from app.models import Device,Telemetry
    from sqlalchemy import select
    application,_=app;client,headers=admin
    with application.state.session_factory() as db:
        for device in db.scalars(select(Device)):
            db.get(Telemetry,device.latest_telemetry_id).active_power_w=0.0
        db.commit()
    response=client.post('/api/v1/strategies',headers=headers,json={'name':'Known-zero synthetic baseline','campus_id':'A','target_reduction_pct':5.0})
    assert response.status_code==201,response.text
    ident=response.json()['data']['id']
    result=client.post(f'/api/v1/strategies/{ident}/evaluate',headers=headers,json={}).json()['data']
    assert result['baseline_kw']==0.0 and result['quality']=='simulation_estimate' and result['baseline_coverage_ratio']==1.0
    with application.state.session_factory() as db:
        db.get(Device,'SIM-A').latest_telemetry_id=None;db.commit()
    result=client.post(f'/api/v1/strategies/{ident}/evaluate',headers=headers,json={}).json()['data']
    assert result['baseline_kw']==0.0 and result['quality']=='partial_simulation_estimate'
    assert result['baseline_coverage_ratio']==.5 and result['target_met'] is False


def test_nullable_or_pre_move_power_is_not_a_current_zero_or_new_building_measurement(app,admin):
    from app.models import Device,Telemetry
    from sqlalchemy import select
    application,_=app;client,headers=admin
    with application.state.session_factory() as db:
        for device in db.scalars(select(Device)):
            db.get(Telemetry,device.latest_telemetry_id).active_power_w=None
        db.commit()
    result=client.get('/api/v1/overview').json()['data']
    assert result['power']['active_kw'] is None and result['power']['source_mode']=='UNKNOWN'
    assert result['power']['meter_count']==0
    with application.state.session_factory() as db:
        device=db.get(Device,'SIM-A');db.get(Telemetry,device.latest_telemetry_id).active_power_w=500.0;db.commit()
    response=client.put('/api/v1/devices/SIM-A/binding',headers=headers,json={'campus_id':'B','building_id':'building-B','reason':'Synthetic observation-time attribution regression'})
    assert response.status_code==200,response.text
    result=client.get('/api/v1/overview?building_id=building-B').json()['data']
    assert result['power']['active_kw'] is None and result['power']['meter_count']==0
