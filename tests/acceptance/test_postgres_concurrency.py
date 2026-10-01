"""PostgreSQL-specific races. Skips explicitly when isolated PG URL is absent."""
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4
from urllib.parse import urlparse

import pytest
from sqlalchemy import select, func, text

from app.common import DomainError
from app.control import create_command, command_dict
from app.db import Base, make_engine, make_session_factory, utcnow
from app.models import Campus, Building, Device, Telemetry, Command, User
from app.registry import add_binding
from app.schemas import CommandIn, TelemetryIn
from app.telemetry import ingest_sample

URL = os.environ.get("ACCEPTANCE_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not URL.startswith("postgresql"), reason="requires disposable PostgreSQL via tools/verify-local.ps1")


@pytest.fixture
def pg():
    parsed=urlparse(URL.replace("postgresql+psycopg://", "postgresql://"))
    if parsed.hostname not in {"127.0.0.1","localhost"} or parsed.username!="qa" or parsed.password or not parsed.path.lstrip("/").startswith("acceptance"):
        raise RuntimeError("Race tests require the disposable loopback qa/acceptance fixture")
    engine = make_engine(URL)
    schema="acceptance_race_"+uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine=engine.execution_options(schema_translate_map={None:schema})
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    ident = uuid4().hex[:16]
    now = utcnow().replace(microsecond=0)
    with factory() as db:
        campus = f"qa-pg-campus-{ident}"
        building = f"qa-pg-building-{ident}"
        device = f"qa-pg-device-{ident}"
        db.add(Campus(id=campus, name="PostgreSQL race fixture", source="local acceptance"))
        db.add(User(id="qa-operator",username="qa-operator",display_name="Local QA operator",role="operator",campus_ids=[campus],enabled=True,is_dev_fixture=False))
        db.flush()
        db.add(Building(id=building, campus_id=campus, name="QA race building", source="local acceptance"))
        db.flush()
        row = Device(id=device, name="QA race device", campus_id=campus, building_id=building, source_mode="SIMULATED", commissioned=True, critical=False, allow_control=True, capabilities=["metering","shed","restore","hold"])
        db.add(row)
        db.flush()
        add_binding(db, row, "qa", "Local race fixture", now-timedelta(days=1))
        db.commit()
    ctx = SimpleNamespace(factory=factory, device_id=device, now=now)
    try:
        yield ctx
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def sample(pg, **changes):
    values = dict(device_id=pg.device_id, boot_epoch="0"*32, sample_seq="0", observed_at=pg.now, time_source="simulated", time_uncertainty_ms=0.0, active_power_w=360.0, voltage_v=230.0, current_a=1.6, energy_import_wh=1000.0, energy_export_wh=0.0, desired_on=True, output_present=True, fault_latched=False, valid=True, calibrated=True, energy_status="known", energy_uncertain_intervals=0, source_mode="SIMULATED", source_version="qa-pg-v1")
    values.update(changes)
    return TelemetryIn(**values)


def races(callables):
    barrier = threading.Barrier(len(callables))
    def run(fn):
        barrier.wait(timeout=10)
        return fn()
    with ThreadPoolExecutor(max_workers=len(callables)) as pool:
        return list(pool.map(run, callables))


def store(pg, value):
    with pg.factory() as db:
        try:
            row, created = ingest_sample(db, value)
            db.commit()
            return ("stored" if created else "duplicate", row.id)
        except DomainError as exc:
            db.rollback()
            return (exc.code, None)


def test_concurrent_same_telemetry_stores_exactly_once(pg):
    value = sample(pg)
    results = races([lambda: store(pg, value) for _ in range(8)])
    assert [x[0] for x in results].count("stored") == 1
    assert [x[0] for x in results].count("duplicate") == 7
    assert len({x[1] for x in results}) == 1
    with pg.factory() as db:
        assert db.scalar(select(func.count()).select_from(Telemetry).where(Telemetry.device_id==pg.device_id)) == 1


def test_concurrent_conflicting_telemetry_rejects_one(pg):
    results = races([lambda: store(pg, sample(pg, energy_import_wh=1000.0)), lambda: store(pg, sample(pg, energy_import_wh=1001.0))])
    assert sorted(x[0] for x in results) == ["stored", "telemetry_conflict"]


def request(pg, key):
    with pg.factory() as db:
        try:
            command, created = create_command(db, CommandIn(device_id=pg.device_id, action="shed", reason="Local PG race", expires_in_seconds=60), key, "qa-operator")
            db.commit()
            return ("created" if created else "duplicate", command.id)
        except DomainError as exc:
            db.rollback()
            return (exc.code, None)


def test_concurrent_same_command_key_returns_same_command(pg):
    store(pg, sample(pg))
    key = "qa-pg-"+uuid4().hex
    results = races([lambda: request(pg, key) for _ in range(6)])
    assert [x[0] for x in results].count("created") == 1
    assert [x[0] for x in results].count("duplicate") == 5, results
    assert len({x[1] for x in results}) == 1


@pytest.mark.parametrize("sequence", [2**31+7, 2**53+7, 2**64-1])
def test_command_sequence_is_uint64_and_json_string(pg, sequence):
    store(pg, sample(pg))
    with pg.factory() as db:
        device = db.get(Device, pg.device_id)
        device.next_command_sequence = sequence
        db.commit()
    result = request(pg, "qa-sequence-"+uuid4().hex)
    assert result[0] == "created"
    with pg.factory() as db:
        command = db.get(Command, result[1])
        assert command_dict(command)["sequence"] == str(sequence)


def test_concurrent_distinct_forecast_keys_cannot_overbook_pending_capacity(pg):
    """Per-key dedupe locks alone cannot protect a shared queue capacity bound."""
    from sqlalchemy import delete
    from app.config import Settings
    from app.forecast_jobs import cached_forecast
    from app.models import ForecastRun, User
    settings=Settings(env="test", worker_enabled=False, forecast_max_pending=16)
    store(pg, sample(pg))
    with pg.factory() as db:
        db.add(User(id="qa-forecast-requester", username="qa-forecast-requester", display_name="Local concurrency fixture",
            role="viewer", campus_ids=None, enabled=True, is_dev_fixture=False))
        db.commit()
    def queue(horizon):
        with pg.factory() as db:
            try:
                result=cached_forecast(db, settings, db.get(User,"qa-forecast-requester"), horizon_hours=horizon)
                db.commit()
                return result['evaluation']['status']
            except DomainError as exc:
                db.rollback()
                return exc.code
    # Repeated synchronized starts exercise independent keys without inserting a
    # test barrier inside the application's lock-protected critical section.
    for _ in range(4):
        with pg.factory() as db:
            db.execute(delete(ForecastRun));db.commit()
        for horizon in range(1,16):
            assert queue(horizon)=="queued"
        results=races([lambda horizon=h:queue(horizon) for h in range(16,20)])
        with pg.factory() as db:
            pending=db.scalar(select(func.count()).select_from(ForecastRun).where(ForecastRun.status.in_(["queued","running"])))
        assert pending==16 and sorted(results)==["forecast_queue_full"]*3+["queued"],(pending,results)
