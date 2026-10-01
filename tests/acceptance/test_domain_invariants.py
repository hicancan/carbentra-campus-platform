"""Independent acceptance: no live hardware, networks, accounts, or production data.

Run from project root: PYTHONPATH=backend backend/.venv/bin/pytest tests/acceptance -q
All fixtures are intentionally local synthetic records. These tests assert observable
invariants, not implementation coverage or a claim of physical qualification.
"""
from datetime import timedelta
import os
from urllib.parse import urlparse
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from app.accounting import compute_energy, ensure_antichain
from app.common import DomainError
from app.control import advance_commands, create_command
from app.db import Base, make_engine, make_session_factory, utcnow
from app.models import Binding, Building, Campus, Circuit, Device, Telemetry, User
from app.registry import add_binding
from app.schemas import CommandIn, TelemetryIn
from app.telemetry import ingest_sample


@pytest.fixture(scope="module")
def postgres_domain_engine():
    url = os.environ.get("ACCEPTANCE_DOMAIN_DATABASE_URL", "")
    if not url.startswith("postgresql"):
        yield None
        return
    parsed = urlparse(url.replace("postgresql+psycopg://", "postgresql://"))
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.username != "qa" or parsed.password or not parsed.path.lstrip("/").startswith("acceptance"):
        raise RuntimeError("Domain PostgreSQL tests require the disposable loopback qa/acceptance fixture")
    engine = make_engine(url)
    schema = "acceptance_domain_"+uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = engine.execution_options(schema_translate_map={None:schema})
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


@pytest.fixture
def domain(postgres_domain_engine):
    engine = postgres_domain_engine if postgres_domain_engine is not None else make_engine("sqlite:///:memory:")
    if postgres_domain_engine is None:
        Base.metadata.create_all(engine)
    connection = engine.connect() if postgres_domain_engine is not None else None
    transaction = connection.begin() if connection else None
    factory = sessionmaker(bind=connection, expire_on_commit=False, autoflush=False, join_transaction_mode="create_savepoint") if connection else make_session_factory(engine)
    with factory() as db:
        now = utcnow().replace(microsecond=0)
        db.add(Campus(id="qa-campus", name="Local QA fixture", source="acceptance"))
        for role in ("operator", "analyst"):
            db.add(User(id="qa-"+role, username="qa-"+role, display_name="Local QA "+role,
                role=role, campus_ids=["qa-campus"], enabled=True, is_dev_fixture=False))
        db.flush()
        for ident in ("qa-building-a", "qa-building-b"):
            db.add(Building(id=ident, campus_id="qa-campus", name=ident, source="acceptance"))
        db.flush()
        db.add(Circuit(id="qa-main", campus_id="qa-campus", building_id="qa-building-a", name="QA main", kind="main"))
        db.flush()
        db.add(Circuit(id="qa-load", campus_id="qa-campus", building_id="qa-building-a", parent_id="qa-main", name="QA load", kind="load"))
        db.flush()
        device = Device(id="qa-device", name="QA simulated plug", campus_id="qa-campus", building_id="qa-building-a", circuit_id="qa-load", kind="smart_plug", source_mode="SIMULATED", commissioned=True, critical=False, allow_control=True, capabilities=["metering", "shed", "restore", "hold"], profile_id="qa-local", profile_revision=1)
        db.add(device)
        db.flush()
        add_binding(db, device, "acceptance", "Local synthetic fixture", now-timedelta(days=2))
        db.commit()
        yield SimpleNamespace(db=db, now=now, device=device)
    if transaction:
        transaction.rollback()
    if connection:
        connection.close()
    if postgres_domain_engine is None:
        engine.dispose()


def sample(ctx, seq, *, at=None, energy=None, boot="0"*32, **changes):
    values = dict(device_id=ctx.device.id, boot_epoch=boot, sample_seq=str(seq), observed_at=at or ctx.now+timedelta(seconds=seq*10), time_source="simulated", time_uncertainty_ms=0.0, active_power_w=360.0, voltage_v=230.0, current_a=1.6, energy_import_wh=float(seq if energy is None else energy), energy_export_wh=0.0, desired_on=True, output_present=True, fault_latched=False, valid=True, calibrated=True, energy_status="known", energy_uncertain_intervals=0, source_mode="SIMULATED", source_version="qa-local-v1")
    values.update(changes)
    return TelemetryIn(**values)


def ingest(ctx, seq, **kw):
    value = sample(ctx, seq, **kw)
    record, created = ingest_sample(ctx.db, value, received_at=max(ctx.now, value.observed_at or ctx.now))
    ctx.db.commit()
    return record, created


def energy(ctx, **scope):
    return compute_energy(ctx.db, start=ctx.now, end=ctx.now+timedelta(seconds=10), **scope)


def assert_error(code, fn):
    with pytest.raises(DomainError) as error:
        fn()
    assert error.value.code == code


def test_wh_is_converted_to_kwh_once(domain):
    ingest(domain, 0, energy=5000)
    ingest(domain, 1, energy=6000)
    result = energy(domain)
    assert result["known_kwh"] == 1.0
    assert result["coverage_ratio"] == 1.0
    assert result["source_mode"] == "SIMULATED"


def test_nonempty_sql_accounting_outputs_are_json_numeric_across_dialects(domain):
    """PG EXTRACT/SUM numeric return types must not leak into public calculations."""
    import json
    from app.accounting import apply_accounting, breakdown, energy_projection
    from app.energy_sql import aggregate_bundle, hourly_totals
    from app.models import CarbonFactor, Tariff
    ingest(domain, 0, energy=5000)
    ingest(domain, 1, energy=6000)
    dates = {"valid_from": domain.now-timedelta(days=1), "valid_to": domain.now+timedelta(days=1)}
    domain.db.add(CarbonFactor(id="qa-factor", name="QA synthetic factor", region="QA", year=2026,
        kg_co2e_per_kwh=0.5, source_url="urn:qa:synthetic", source_mode="SIMULATED", version=1, **dates))
    domain.db.add(Tariff(id="qa-tariff", name="QA synthetic tariff", currency="CNY", rate_per_kwh=0.75,
        timezone="Asia/Shanghai", bands=[], source_url="urn:qa:synthetic", source_mode="SIMULATED", version=1, **dates))
    domain.db.commit()
    scope = {"start": domain.now, "end": domain.now+timedelta(seconds=10)}
    carbon = apply_accounting(domain.db, "carbon", **scope)
    cost = apply_accounting(domain.db, "cost", **scope)
    _, _, _, projection, _ = energy_projection(domain.db, **scope)
    hourly = hourly_totals(domain.db, projection)
    bundle = aggregate_bundle(domain.db, projection, overview=True)
    grouped = breakdown(domain.db, **scope)
    assert carbon["kg_co2e"] == 0.5 and carbon["reduction_claim"] is False
    assert cost["amount"] == 0.75 and cost["pricing_coverage_ratio"] == 1.0
    assert hourly[0]["known_kwh"] == 1.0 and hourly[0]["active_kw"] == 360.0
    assert bundle["totals"]["known"] == 1.0 and bundle["totals"]["count"] == 1
    assert bundle["trend"] == hourly
    assert grouped[0]["known_kwh"] == 1.0 and grouped[0]["coverage_ratio"] == 1.0
    json.dumps({"carbon": carbon, "cost": cost, "hourly": hourly, "grouped": grouped, "overview_trend": bundle["trend"]}, allow_nan=False)


def test_cross_campus_history_sql_only_counts_authorized_binding_intervals(domain):
    from app import scoping  # Register the same ORM authorization listener as app startup.
    from app.accounting import breakdown
    ingest(domain, 0, energy=5000)
    ingest(domain, 1, energy=6000)
    domain.db.add(Campus(id="qa-campus-other", name="QA other campus", source="acceptance"))
    domain.db.flush()
    domain.db.add(Building(id="qa-building-other", campus_id="qa-campus-other", name="QA other building", source="acceptance"))
    domain.db.flush()
    domain.db.add(Circuit(id="qa-circuit-other", campus_id="qa-campus-other", building_id="qa-building-other", name="QA other circuit", kind="load"))
    domain.db.flush()
    domain.device.campus_id="qa-campus-other"
    domain.device.building_id="qa-building-other"
    domain.device.circuit_id="qa-circuit-other"
    add_binding(domain.db, domain.device, "acceptance", "QA historical campus move", domain.now+timedelta(seconds=20))
    domain.db.commit()
    ingest(domain, 2, energy=7000)
    ingest(domain, 3, energy=17000)
    scope={"start": domain.now, "end": domain.now+timedelta(seconds=30)}
    for campuses, expected, building in [(["qa-campus"], 1.0, "qa-building-a"), (["qa-campus-other"], 10.0, "qa-building-other")]:
        domain.db.info["campus_ids"]=campuses
        result=compute_energy(domain.db, **scope)
        assert result["known_kwh"] == expected
        assert compute_energy(domain.db, device_ids=[domain.device.id], **scope)["known_kwh"] == expected
        assert {row["id"] for row in breakdown(domain.db, **scope)} == {building}
    domain.db.info["campus_ids"]=[]
    assert compute_energy(domain.db, **scope)["known_kwh"] is None
    domain.db.info.pop("campus_ids")
    assert compute_energy(domain.db, **scope)["known_kwh"] == 11.0


def test_first_postupgrade_sample_does_not_hide_preexisting_raw_history_from_projection_bootstrap(domain):
    from sqlalchemy import delete
    from app.forecast_jobs import inputs
    from app.models import ForecastDirtyHour, ForecastHourRevision, ForecastProjectionState
    from app.projection import hour, queue_history
    ingest(domain, 0, at=domain.now-timedelta(hours=4), energy=1000)
    ingest(domain, 1, at=domain.now-timedelta(hours=3), energy=1001)
    # Simulate an upgraded existing ledger: raw evidence exists, while the newly
    # introduced derived tables are empty. No raw measurement is deleted.
    for model in (ForecastDirtyHour, ForecastHourRevision, ForecastProjectionState):
        domain.db.execute(delete(model))
    domain.db.commit()
    ingest(domain, 2, at=domain.now, energy=1002)
    state=domain.db.get(ForecastProjectionState, domain.device.id)
    assert state is not None and not state.history_initialized
    _,_,_,cold=inputs(domain.db, None, None, domain.now)
    assert domain.device.id in cold, 'Fresh telemetry-created state must not suppress historical bootstrap'
    queued=queue_history(domain.db, cold, now=domain.now)
    assert queued['hours_marked'] >= 4
    assert domain.db.scalar(select(ForecastDirtyHour.hour_end).where(
        ForecastDirtyHour.device_id==domain.device.id,
        ForecastDirtyHour.hour_end <= hour(domain.now)-timedelta(hours=2))) is not None


def test_live_power_cannot_be_labeled_simulated_when_it_includes_real_measurements(domain):
    from app.analytics import overview
    from app.config import Settings
    ingest(domain,0,at=domain.now-timedelta(seconds=10),energy=1000,active_power_w=360.0)
    ingest(domain,1,at=domain.now,energy=1001,active_power_w=360.0)
    domain.db.add(Circuit(id='qa-real-boundary',campus_id='qa-campus',building_id='qa-building-a',name='Separate inert QA boundary',kind='main'))
    domain.db.flush()
    real=Device(id='QA-INERT-REAL-METER',name='Synthetic fixture labeled REAL, never actuated',campus_id='qa-campus',building_id='qa-building-a',
        circuit_id='qa-real-boundary',kind='meter',source_mode='REAL',dispatch_mode='DISABLED',commissioned=False,critical=True,allow_control=False,capabilities=['metering'])
    domain.db.add(real);domain.db.flush()
    add_binding(domain.db,real,'acceptance','Separate synthetic measurement boundary',domain.now-timedelta(days=2))
    domain.db.commit()
    real_context=SimpleNamespace(db=domain.db,now=domain.now,device=real)
    ingest(real_context,0,at=domain.now,source_mode='REAL',time_source='authenticated',active_power_w=1440.0)
    result=overview(domain.db,Settings(env='test',worker_enabled=False))
    assert result['energy']['source_mode']=='SIMULATED', 'The single REAL sample has no eligible energy interval yet'
    assert result['power']['active_kw']==1.8 and result['power']['meter_count']==2
    assert result.get('source_mode')=='MIXED' or result['power'].get('source_mode')=='MIXED', 'Mixed live power inherited the simulation-only historical energy label'


def test_duplicate_identity_is_durable_and_changed_payload_rejected(domain):
    first, created = ingest(domain, 0, energy=5000)
    assert created
    again, created = ingest(domain, 0, energy=5000)
    assert not created and again.id == first.id
    assert_error("telemetry_conflict", lambda: ingest(domain, 0, energy=5001))
    assert len(domain.db.scalars(select(Telemetry)).all()) == 1


@pytest.mark.parametrize("change,reason", [
    ({"boot": "1"*32}, "boot_boundary"),
    ({"energy": 9}, "counter_regression"),
    ({"energy_uncertain_intervals": 1}, "uncertain_energy_interval"),
    ({"calibrated": False}, "quality_excluded"),
    ({"time_uncertainty_ms": 6000.0}, "quality_excluded"),
    ({"valid": False}, "quality_excluded"),
])
def test_unknown_and_reset_intervals_are_not_zero_or_billable(domain, change, reason):
    ingest(domain, 0, energy=10)
    ingest(domain, 1, **({"energy": 20} | change))
    result = energy(domain)
    assert result["known_kwh"] is None
    assert result["quality"] == "unknown"
    assert f"{reason}:1" in result["warnings"]


def test_gap_is_excluded_not_integrated(domain):
    ingest(domain, 0, energy=10)
    ingest(domain, 1, at=domain.now+timedelta(seconds=1801), energy=9999)
    result = compute_energy(domain.db, start=domain.now, end=domain.now+timedelta(seconds=1801))
    assert result["known_kwh"] is None
    assert "coverage_gap:1" in result["warnings"]


def test_parent_meter_and_descendant_load_cannot_be_summed(domain):
    meter = Device(id="qa-meter", name="QA meter", campus_id="qa-campus", building_id="qa-building-a", circuit_id="qa-main", kind="meter", source_mode="SIMULATED", capabilities=["metering"])
    domain.db.add(meter)
    domain.db.commit()
    assert_error("double_counting", lambda: energy(domain, device_ids=[meter.id, domain.device.id]))
    assert energy(domain)["selected_device_ids"] == [meter.id]


def test_topology_cycle_is_explicitly_rejected(domain):
    domain.db.get(Circuit, "qa-main").parent_id = "qa-load"
    domain.db.commit()
    assert_error("topology_cycle", lambda: energy(domain))


def test_historical_building_energy_survives_current_device_move(domain):
    ingest(domain, 0, energy=1000)
    ingest(domain, 1, energy=2000)
    domain.device.building_id = "qa-building-b"
    domain.device.circuit_id = None
    add_binding(domain.db, domain.device, "acceptance", "Synthetic movement", domain.now+timedelta(seconds=20))
    domain.db.commit()
    result = energy(domain, building_id="qa-building-a")
    assert result["known_kwh"] == 1.0, "Historical energy must use placement at observation, even after a device moves away"


def make_command(ctx, key="qa-command-0001", **changes):
    payload = dict(device_id=ctx.device.id, action="shed", expires_in_seconds=30, reason="Local acceptance simulation", simulation_scenario="success")
    payload.update(changes)
    result = create_command(ctx.db, CommandIn(**payload), key, "qa-operator", now=ctx.now+timedelta(seconds=1))
    ctx.db.commit()
    return result


def test_command_ttl_and_idempotency(domain):
    ingest(domain, 0)
    first, created = make_command(domain)
    assert created
    same, created = make_command(domain)
    assert not created and same.id == first.id
    assert_error("idempotency_conflict", lambda: make_command(domain, action="restore"))
    advance_commands(domain.db, domain.now+timedelta(seconds=31))
    domain.db.commit()
    assert first.status == "timed_out"
    assert first.result is None


@pytest.mark.parametrize('dispatch_mode',['IN_PROCESS','VIRTUAL'])
def test_orphaned_issuer_cannot_dispatch_a_persisted_command(domain,dispatch_mode):
    from app.adapter import poll_commands
    from app.config import Settings
    domain.device.dispatch_mode=dispatch_mode
    ingest(domain,0)
    command,_=make_command(domain,action='hold')
    domain.db.delete(domain.db.get(User,'qa-operator'))
    domain.db.commit()
    if dispatch_mode=='IN_PROCESS':
        advance_commands(domain.db,domain.now+timedelta(seconds=2))
    else:
        assert poll_commands(domain.db,Settings(env='test',worker_enabled=False),[domain.device.id],now=domain.now+timedelta(seconds=2))==[]
    domain.db.commit()
    assert command.status=='rejected' and command.result is None
    assert all(step['status'] not in {'dispatched','acknowledged','verified'} for step in command.history)


@pytest.mark.parametrize("field,value,code", [
    ("source_mode", "REAL", "physical_control_disabled"),
    ("source_mode", "REPLAYED", "physical_control_disabled"),
    ("critical", True, "critical_load"),
    ("commissioned", False, "not_commissioned"),
    ("allow_control", False, "control_not_authorized"),
])
def test_control_rejects_ineligible_devices(domain, field, value, code):
    ingest(domain, 0)
    setattr(domain.device, field, value)
    domain.db.commit()
    assert_error(code, lambda: make_command(domain))


def test_rebinding_after_request_fails_closed(domain):
    ingest(domain, 0)
    command, _ = make_command(domain)
    domain.device.profile_revision += 1
    domain.db.commit()
    advance_commands(domain.db, domain.now+timedelta(seconds=2))
    assert command.status == "rejected"


def test_verified_command_requires_fresh_correlated_observation(domain):
    """A result fabricated from command intent is not independent feedback evidence."""
    old, _ = ingest(domain, 0)
    command, _ = make_command(domain)
    for seconds in (2, 3, 4):
        advance_commands(domain.db, domain.now+timedelta(seconds=seconds))
        domain.db.commit()
    assert command.status == "verified", "A canonical successful simulation must reach verified with real persisted simulated feedback"
    if command.status == "verified":
        evidence = command.history[-1]["evidence"]
        observation_id = evidence.get("telemetry_id") or evidence.get("observation_id")
        assert observation_id, "Verified state must reference persisted feedback evidence, not copied desired state"
        observation = domain.db.get(Telemetry, observation_id)
        assert observation is not None and observation.id != old.id
        assert observation.observed_at > command.issued_at
        assert observation.received_at > command.issued_at
        assert observation.raw_payload.get("command_id") == command.id
        assert str(observation.raw_payload.get("command_sequence")) == str(command.sequence)
    else:
        assert command.status in {"acknowledged", "failed", "timed_out"}


def test_late_telemetry_uses_observed_time_binding_not_current_placement(domain):
    old_binding = domain.db.scalar(select(Binding).where(Binding.device_id==domain.device.id))
    domain.device.building_id = "qa-building-b"
    domain.device.circuit_id = None
    new_binding = add_binding(domain.db, domain.device, "acceptance", "Synthetic movement", domain.now+timedelta(seconds=10))
    domain.db.commit()
    late = sample(domain, 0, at=domain.now, energy=1000)
    stored, _ = ingest_sample(domain.db, late, received_at=domain.now+timedelta(seconds=30))
    domain.db.commit()
    assert stored.building_id == "qa-building-a"
    assert stored.binding_id == old_binding.id and stored.binding_id != new_binding.id


def test_older_late_observation_never_supersedes_latest_state(domain):
    newer, _ = ingest(domain, 2, energy=2000)
    older = sample(domain, 1, energy=1000)
    ingest_sample(domain.db, older, received_at=domain.now+timedelta(seconds=30))
    domain.db.commit()
    assert domain.device.latest_telemetry_id == newer.id
    assert domain.device.last_seen_at == domain.now+timedelta(seconds=30)


def test_future_and_untrusted_clock_samples_do_not_enter_known_energy(domain):
    first = sample(domain, 0, at=domain.now+timedelta(hours=1), energy=1000)
    second = sample(domain, 1, at=domain.now+timedelta(hours=1, seconds=10), energy=2000)
    for value in (first, second):
        stored, _ = ingest_sample(domain.db, value, received_at=domain.now)
        assert "FUTURE_TIMESTAMP" in stored.quality_flags
    domain.db.commit()
    result = compute_energy(domain.db, start=first.observed_at, end=second.observed_at)
    assert result["known_kwh"] is None


def test_adapter_cannot_verify_without_persisted_fresh_feedback(domain):
    from app.adapter import store_ack
    from app.simulation import output_state, raw_ack
    ingest(domain, 0)
    command, _ = make_command(domain)
    advance_commands(domain.db, domain.now+timedelta(seconds=2))
    advance_commands(domain.db, domain.now+timedelta(seconds=3))
    domain.db.commit()
    assert command.status == "acknowledged"
    state = output_state(domain.db, domain.device)
    state.output_present = state.desired_on
    raw = raw_ack(command, domain.device, state, "OBSERVED_VERIFIED", domain.now+timedelta(seconds=4))
    assert_error("observation_required", lambda: store_ack(domain.db, raw, domain.now+timedelta(seconds=4)))
    domain.db.rollback()
    assert command.status == "acknowledged"


def test_uncorrelated_ack_is_preserved_but_does_not_verify(domain):
    from app.adapter import store_ack
    from app.simulation import output_state, raw_ack
    ingest(domain, 0)
    command, _ = make_command(domain)
    advance_commands(domain.db, domain.now+timedelta(seconds=2))
    advance_commands(domain.db, domain.now+timedelta(seconds=3))
    domain.db.commit()
    state = output_state(domain.db, domain.device)
    state.output_present = state.desired_on
    raw = raw_ack(command, domain.device, state, "OBSERVED_VERIFIED", domain.now+timedelta(seconds=4))
    raw["seq"] = str(command.sequence+1)
    observation, created = store_ack(domain.db, raw, domain.now+timedelta(seconds=4))
    domain.db.commit()
    assert created and not observation.matched
    assert command.status == "acknowledged"


def test_strategy_baseline_does_not_double_count_parent_and_child_meters(domain):
    from app.control import evaluate_strategy
    from app.models import Strategy
    ingest(domain,0,active_power_w=200.0)
    for ident,circuit,power in [('qa-meter-parent','qa-main',1000.0),('qa-meter-child','qa-load',400.0)]:
        meter=Device(id=ident,name='QA strategy meter',campus_id='qa-campus',building_id='qa-building-a',circuit_id=circuit,kind='meter',source_mode='SIMULATED',capabilities=['metering'])
        domain.db.add(meter);domain.db.flush()
        add_binding(domain.db,meter,'acceptance','QA meter baseline',domain.now-timedelta(days=1))
        ingest(SimpleNamespace(db=domain.db,now=domain.now,device=meter),0,active_power_w=power)
    strategy=Strategy(id='qa-strategy-baseline',name='QA strategy baseline',campus_id='qa-campus',target_reduction_pct=20.0,max_devices=5,created_by='qa-analyst')
    domain.db.add(strategy);domain.db.flush()
    evaluation=evaluate_strategy(domain.db,strategy,'qa-analyst',now=domain.now+timedelta(seconds=1))
    assert evaluation['baseline_kw']==1.0,'Strategy baseline counted both parent and descendant meters'


def test_same_boot_lower_sequence_cannot_replace_latest_via_later_wall_clock(domain):
    newest,_=ingest(domain,2,at=domain.now+timedelta(seconds=20),energy=2000)
    lower=sample(domain,1,at=domain.now+timedelta(seconds=30),energy=1000)
    ingest_sample(domain.db,lower,received_at=domain.now+timedelta(seconds=30))
    domain.db.commit()
    assert domain.device.latest_telemetry_id==newest.id,'Lower same-boot sequence replaced trusted latest state via a later wall-clock timestamp'


@pytest.mark.parametrize('change',['profile','stale'])
def test_virtual_delivery_lease_rechecks_safety_at_dispatch_boundary(domain,change):
    from app.adapter import poll_commands
    from app.config import Settings
    domain.device.dispatch_mode='VIRTUAL'
    ingest(domain,0,at=domain.now-timedelta(seconds=9) if change=='stale' else domain.now)
    command,_=make_command(domain,expires_in_seconds=60)
    now=domain.now+timedelta(seconds=2)
    if change=='profile':
        domain.device.profile_revision+=1
        domain.device.critical=True
        domain.device.allow_control=False
    domain.db.commit()
    leased=poll_commands(domain.db,Settings(env='test'),[domain.device.id],now=now)
    assert leased==[],'Adapter leased a command after dispatch-time safety became invalid'
    assert command.status in {'rejected','failed','timed_out'}


def test_building_breakdown_coverage_includes_missing_measurement_boundaries(domain):
    from app.accounting import breakdown
    domain.db.add(Circuit(id='qa-missing-main',campus_id='qa-campus',building_id='qa-building-a',name='QA missing boundary',kind='main'))
    domain.db.flush()
    missing=Device(id='qa-missing-meter',name='QA missing meter',campus_id='qa-campus',building_id='qa-building-a',circuit_id='qa-missing-main',kind='meter',source_mode='SIMULATED',capabilities=['metering'])
    domain.db.add(missing);domain.db.flush()
    add_binding(domain.db,missing,'qa','QA missing meter boundary',domain.now-timedelta(days=1))
    ingest(domain,0,energy=1000);ingest(domain,1,energy=2000)
    summary=energy(domain)
    assert summary['coverage_ratio']==0.5
    rows=breakdown(domain.db,'building',start=domain.now,end=domain.now+timedelta(seconds=10))
    assert rows[0]['coverage_ratio']==0.5,'Breakdown silently dropped the entirely missing meter from its denominator'
    assert rows[0]['quality']=='partial'


def test_rebound_load_uses_interval_specific_antichain_not_flat_device_ids(domain):
    meter=Device(id='qa-history-parent',name='QA historical parent meter',campus_id='qa-campus',building_id='qa-building-a',circuit_id='qa-main',kind='meter',source_mode='SIMULATED',capabilities=['metering'])
    domain.db.add(meter);domain.db.flush()
    add_binding(domain.db,meter,'qa','QA parent measurement boundary',domain.now-timedelta(days=1))
    parent=SimpleNamespace(db=domain.db,now=domain.now,device=meter)
    for seq in range(4):ingest(parent,seq,energy=1000+seq*10,active_power_w=3600.0)
    ingest(domain,0,energy=100);ingest(domain,1,energy=101)
    domain.db.add(Circuit(id='qa-history-independent',campus_id='qa-campus',building_id='qa-building-a',name='QA independent boundary',kind='load'))
    domain.db.flush();domain.device.circuit_id='qa-history-independent'
    add_binding(domain.db,domain.device,'qa','QA independently supplied after move',domain.now+timedelta(seconds=15))
    domain.db.commit()
    ingest(domain,2,energy=102);ingest(domain,3,energy=103)
    result=compute_energy(domain.db,start=domain.now,end=domain.now+timedelta(seconds=30))
    assert result['known_kwh']==0.031,'Historical child interval was summed again after its device later moved outside parent boundary'


def test_accounting_source_mode_comes_from_immutable_measurements(domain):
    ingest(domain,0,energy=1000);ingest(domain,1,energy=2000)
    # Out-of-band import/migration drift must not relabel old evidence as REAL.
    domain.device.source_mode='REAL';domain.db.commit()
    result=energy(domain)
    assert result['known_kwh']==1.0
    assert result['source_mode']=='SIMULATED','Current registry metadata relabeled historical simulated measurements as REAL'


def test_late_old_boot_fault_does_not_create_current_alarm_at_new_location(domain):
    from app.models import Alarm
    ingest(domain,1,at=domain.now,boot='b'*32,fault_latched=False)
    domain.device.building_id='qa-building-b';domain.device.circuit_id=None
    add_binding(domain.db,domain.device,'qa','QA moved device after historical epoch',domain.now+timedelta(seconds=10))
    domain.db.commit()
    current,_=ingest(domain,2,at=domain.now+timedelta(seconds=20),boot='b'*32,fault_latched=False)
    old=sample(domain,99,at=domain.now-timedelta(seconds=10),boot='a'*32,fault_latched=True)
    historical,_=ingest_sample(domain.db,old,received_at=domain.now+timedelta(seconds=30))
    domain.db.commit()
    assert historical.building_id=='qa-building-a'
    assert domain.device.latest_telemetry_id==current.id
    alarms=domain.db.scalars(select(Alarm).where(Alarm.device_id==domain.device.id)).all()
    assert not [a for a in alarms if a.type=='local_fault' and a.status!='resolved'],'Late superseded fault became an active current fault'
    assert all(a.building_id=='qa-building-a' for a in alarms),'Historical fault was attributed to the current location'


def test_correlated_virtual_ack_can_arrive_before_broker_delivery_receipt(domain):
    from app.adapter import poll_commands,store_ack,record_delivery
    from app.config import Settings
    from app.schemas import DeliveryIn
    domain.device.dispatch_mode='VIRTUAL'
    ingest(domain,0)
    command,_=make_command(domain,action='hold')
    lease=poll_commands(domain.db,Settings(env='test'),[domain.device.id],now=domain.now+timedelta(seconds=2))[0]
    domain.db.commit()
    assert command.status=='requested'
    ack={'schema_version':2,'device_id':domain.device.id,'boot_epoch':command.expected_boot_epoch,'id':command.id,'seq':str(command.sequence),'status':'REQUESTED_AWAITING_FEEDBACK','terminal':False,'desired_on':True,'fault_latched':False,'voltage_absence_proven':False,'requested_monotonic_ms':1000,'deadline_monotonic_ms':6000}
    store_ack(domain.db,ack,received_at=domain.now+timedelta(seconds=3));domain.db.commit()
    assert command.status=='acknowledged'
    terminal=ack|{'status':'OBSERVED_VERIFIED','terminal':True,'observed_monotonic_ms':1200,'feedback_valid':True,'output_present':True,'output_sensing':'AC_PRESENT'}
    store_ack(domain.db,terminal,received_at=domain.now+timedelta(seconds=3.2));domain.db.commit()
    assert command.status=='verified'
    receipt=record_delivery(domain.db,command.id,DeliveryIn(lease_id=lease['lease_id'],status='published'),[domain.device.id],now=domain.now+timedelta(seconds=4))
    domain.db.commit()
    assert receipt['status']=='verified' and receipt['durable'] is True
    assert [h['status'] for h in command.history]==['requested','dispatched','acknowledged','verified']


@pytest.mark.parametrize('configuration,expected', [
    ('overlap', None), ('partial_boundary', None), ('adjacent_versions', None), ('separate_source', 0.5),
])
def test_carbon_fast_reference_path_retains_ambiguity_and_source_boundaries(domain, configuration, expected):
    """An imported overlapping factor must not become a falsely exact total."""
    from app.accounting import apply_accounting
    from app.models import CarbonFactor
    ingest(domain, 0, energy=1000)
    ingest(domain, 1, energy=2000)
    def factor(ident, start, end, rate=.5, source='SIMULATED'):
        domain.db.add(CarbonFactor(id=ident,name='Synthetic reference boundary',region='QA',year=2026,
            kg_co2e_per_kwh=rate,valid_from=start,valid_to=end,source_url='https://example.invalid/qa-factor',source_mode=source,version=1))
    start,end=domain.now,domain.now+timedelta(seconds=10)
    if configuration in {'partial_boundary','adjacent_versions'}:
        factor('qa-left',start-timedelta(hours=1),start+timedelta(seconds=5))
        if configuration=='adjacent_versions':factor('qa-right',start+timedelta(seconds=5),end+timedelta(hours=1),.7)
    else:
        factor('qa-reference',start-timedelta(hours=1),end+timedelta(hours=1))
        factor('qa-other',start-timedelta(hours=1),end+timedelta(hours=1),.7,
            'REAL' if configuration=='separate_source' else 'SIMULATED')
    domain.db.commit()
    result=apply_accounting(domain.db,'carbon',start=start,end=end)
    assert result['known_kwh']==1.0 and result['kg_co2e']==expected
    assert result['source_mode']=='SIMULATED' and result['reduction_claim'] is False
    if expected is None:assert result['quality']=='unavailable'
    else:assert result['factor_id']=='qa-reference'
