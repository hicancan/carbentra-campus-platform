"""Isolated in-memory HTTP/software transport proof. NO physical device or broker is used."""
from datetime import timedelta
import time
from app.db import utcnow
from app.models import Device, Audit
from sqlalchemy import select
from app.telemetry import normalize_firmware, ingest_sample
from app.adapter import physical_released

P="/api/v1"


def test_future_real_transport_requires_independent_deployment_and_device_release(app, admin):
    application, _ = app
    client, headers = admin
    ident = "REAL-FAKE-QA"
    response = client.post(P+"/devices",headers=headers,json={"id":ident,"name":"INERT software fixture, no actual device","campus_id":"A","building_id":"building-A","kind":"smart_plug","source_mode":"REAL","capabilities":["metering","hold","shed","restore"]})
    assert response.status_code==201,response.text
    # This is synthetic wire input in a disposable test database, explicitly not
    # real calibration/safety evidence. The deployed environment remains OFF.
    time.sleep(1.05)  # Device was registered before its first whole-second wire timestamp
    now=utcnow()
    epoch=int(now.timestamp())
    raw={"schema_version":2,"device_id":ident,"boot_epoch":"b"*32,"sample_seq":"1","board_revision":"CARBENTRA-P16-EVT-B",
        "valid":True,"calibrated":True,"monotonic_ms":5000,"measurement_monotonic_ms":5000,"time_quality":"authenticated","unix_s":epoch,"unix_lower_s":epoch-1,"unix_upper_s":epoch+1,
        "fault_latched":False,"board_temperature_valid":True,"board_temperature_c":28.0,"desired_on":True,"feedback_valid":True,"output_present":True,"output_sensing":"AC_PRESENT","voltage_absence_proven":False,
        "voltage_v":230.0,"current_a":1.0,"active_w":225.0,"reactive_var":10.0,"apparent_va":230.0,"pf":.98,"frequency_hz":50.0,
        "ram_buffer_dropped":0,"command_dropped":0,"energy_status":"calibrated_counts_known_intervals_since_boot_not_billing_certified","known_forward_wh_since_boot":10.0,"known_reverse_wh_since_boot":0.0,"energy_uncertain_intervals":0}
    with application.state.session_factory() as db:
        ingest_sample(db,normalize_firmware(raw),raw_payload=raw)
        db.commit()
    create={"id":"release-test-only","profile_id":"inert-qa-profile","load_id":"inert-load-fixture","load_name":"INERT test load; no physical connection","hardware_revision":"CARBENTRA-P16-EVT-B","safety_assessment_ref":"TEST ONLY: no physical safety qualification",
        "installation_approval_ref":"TEST ONLY: no physical installation", "calibration_ref":"TEST ONLY: no physical calibration", "valid_until":(now+timedelta(days=1)).isoformat()}
    response=client.post(P+f"/devices/{ident}/commissioning",headers=headers,json=create)
    assert response.status_code==201,response.text
    release={"release_id":create["id"],"operator_attested":True,"noncritical_load_attested":True,"note":"Inert isolated code-path test only"}
    assert client.post(P+f"/devices/{ident}/commissioning/release",headers=headers,json=release).status_code==409
    settings=application.state.settings
    settings.physical_dispatch_enabled=True
    assert client.post(P+f"/devices/{ident}/commissioning/release",headers=headers,json=release).status_code==409
    settings.physical_release_ids=[create["id"]]
    assert client.post(P+f"/devices/{ident}/commissioning/release",headers=headers,json=release|{"operator_attested":False}).status_code==409
    response=client.post(P+f"/devices/{ident}/commissioning/release",headers=headers,json=release)
    assert response.status_code==200,response.text
    settings.adapter_allowed_device_ids.append(ident)
    reviewed=client.get(P+f"/devices/{ident}/control-eligibility").json()["data"]
    confirmation={"device_id":ident,"release_id":create["id"],"profile_revision":reviewed["profile_revision"],"load_id":"inert-load-fixture","action":"shed","understands_mains_consequence":True}
    command_body={"device_id":ident,"action":"shed","reason":"Software-only transport contract test","physical_confirmation":confirmation}
    for changes in ({"release_id":"replaced-release-identity"},{"profile_revision":reviewed["profile_revision"]+1}):
        stale=client.post(P+"/commands",headers=headers|{"Idempotency-Key":"inert-stale-review"},json=command_body|{"physical_confirmation":confirmation|changes})
        assert stale.status_code==409 and stale.json()["error"]["code"]=="physical_review_stale"
    with application.state.session_factory() as db:
        device=db.get(Device,ident);device.profile_revision+=1;db.commit()
    stale=client.post(P+"/commands",headers=headers|{"Idempotency-Key":"inert-stale-after-change"},json=command_body)
    assert stale.status_code==409 and stale.json()["error"]["code"]=="physical_review_stale"
    with application.state.session_factory() as db:
        from app.models import Command
        assert not db.scalars(select(Command).where(Command.device_id==ident)).all()
    confirmation["profile_revision"]=client.get(P+f"/devices/{ident}/control-eligibility").json()["data"]["profile_revision"]
    command=client.post(P+"/commands",headers=headers|{"Idempotency-Key":"inert-physical-path"},json=command_body)
    assert command.status_code==201,command.text
    frozen=command.json()["data"]["history"][0]["evidence"]
    assert frozen["release_id"]==create["id"] and frozen["load_id"]==create["load_id"] and frozen["load_name"]==create["load_name"]
    assert frozen["physical_review_confirmed"] is True
    with application.state.session_factory() as db:
        entry=db.scalar(select(Audit).where(Audit.entity_id==command.json()["data"]["id"],Audit.action=="requested"))
        assert entry.details["simulated"] is False and entry.details["source_mode"]=="REAL"
    auth={"Authorization":"Bearer unit-test-fixture-token-not-real-secret-123"}
    items=client.get(P+"/adapter/commands",headers=auth).json()["data"]
    item=next(x for x in items if x["id"]==command.json()["data"]["id"])
    assert item["dispatch_mode"]=="PHYSICAL" and item["source_mode"]=="REAL" and item["release_id"]==create["id"]
    # No delivery/publication occurs. Revoke immediately in the disposable fixture.
    response=client.post(P+f"/devices/{ident}/commissioning/{create['id']}/revoke",headers=headers,json={"note":"Close inert test gate"})
    assert response.status_code==200,response.text
    with application.state.session_factory() as db:
        device=db.get(Device,ident)
        assert not physical_released(device,settings,db) and not device.allow_control
    settings.physical_dispatch_enabled=False
    settings.physical_release_ids=[]
