"""Local deterministic fixtures only; no actual campus data or control hardware."""
from datetime import datetime, timedelta, timezone
import json
import math
import os
from uuid import uuid4
from types import SimpleNamespace

import pytest
from sqlalchemy import String, cast, delete, func, insert, select, text, update

from app import forecasting as forecasting_module
from app.common import DomainError
from app.db import Base, make_engine, make_session_factory
from app.forecasting import _available_history, _backtest, _positive_area, forecast
from app.models import Binding, Building, Campus, Circuit, Command, Device, Telemetry

NOW = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)


@pytest.fixture
def fixture():
    url = os.environ.get("FORECAST_TEST_POSTGRES_URL", "sqlite:///:memory:")
    engine = make_engine(url)
    schema = "forecast_test_" + uuid4().hex if url.startswith("postgresql") else None
    if schema:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = engine.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as db:
        db.add(Campus(id="campus", name="Synthetic QA campus", source="test", timezone="Asia/Shanghai"))
        db.flush()
        db.add_all([Building(id=ident, campus_id="campus", name=ident, source="test") for ident in ["building", "other-building"]])
        db.commit()
        yield SimpleNamespace(db=db, now=NOW, schema=schema)
    if schema:
        if os.environ.get("FORECAST_KEEP_SCHEMA") == "1" and os.environ.get("FORECAST_SCALE_METERS"):
            print(f"RETAINED_FORECAST_SCHEMA={schema}", flush=True)
        else:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


def add_meter(fixture, ident="meter", *, parent=None, building="building", mode="SIMULATED"):
    db = fixture.db
    circuit_id = f"circuit-{ident}"
    db.add(Circuit(id=circuit_id, campus_id="campus", building_id=building, parent_id=parent, name=ident, kind="branch"))
    db.flush()
    device = Device(id=ident, name=ident, campus_id="campus", building_id=building, circuit_id=circuit_id,
                    kind="meter", source_mode=mode, capabilities=["metering"], commissioned=True,
                    provenance={"synthetic": True})
    db.add(device)
    db.flush()
    binding = Binding(device_id=ident, campus_id="campus", building_id=building, circuit_id=circuit_id,
                      valid_from=NOW - timedelta(days=30), actor="test", reason="Synthetic fixture")
    db.add(binding)
    db.commit()
    return device, binding


def add_history(fixture, device=None, *, ident="meter", days=14, power=None, changes=None, shift=timedelta(), step_seconds=1800):
    device, binding = device or add_meter(fixture, ident)
    power = power or (lambda at: 8000 + 1800 * math.sin(2 * math.pi * at.hour / 24) + 50 * (at - (NOW - timedelta(days=14))).total_seconds() / 3600)
    start, end = NOW - timedelta(days=days) + shift, NOW + shift
    rows = []
    for seq in range(int((end - start).total_seconds() / step_seconds) + 1):
        at = start + timedelta(seconds=seq * step_seconds)
        watts = power(at)
        row = dict(device_id=device.id, boot_epoch="epoch", sample_seq=str(seq), observed_at=at, received_at=at,
                   active_power_w=watts, quality="good", quality_flags=[], time_source="simulated" if device.source_mode == "SIMULATED" else "authenticated",
                   time_uncertainty_ms=0.0, raw_payload={"valid": True, "calibrated": True}, payload_hash="test",
                   source_mode=device.source_mode, source_version="synthetic-test-v1", binding_id=binding.id,
                   campus_id="campus", building_id=device.building_id, circuit_id=device.circuit_id)
        if changes:
            row.update(changes(at, seq) if callable(changes) else changes)
        rows.append(row)
    fixture.db.execute(insert(Telemetry), rows)
    fixture.db.commit()
    return device, binding


def run(fixture, **kwargs):
    return forecast(fixture.db, campus_id="campus", building_id="building", now=NOW, **kwargs)


def test_trains_real_ridge_with_disjoint_selection_and_holdout(fixture):
    add_history(fixture)
    result = run(fixture)
    assert result["model"]["trained"] is True
    assert result["model"]["training_sample_count"] > 200
    assert result["method"] == "ridge_regression"
    assert result["quality"] == "model_estimate"
    assert result["coverage"]["device_ratio"] == 1
    assert result["coverage"]["hour_ratio"] == 1
    assert result["holdout"]["sample_count"] == 48
    assert result["holdout"]["selection_used_holdout"] is False
    assert result["model"]["validation"]["end"] < result["holdout"]["start"]
    assert result["holdout"]["models"]["ridge_regression"]["mae_kw"] < result["holdout"]["models"]["seasonal_naive"]["mae_kw"]
    assert result["mae_kw"] == result["holdout"]["models"][result["method"]]["mae_kw"]
    assert result["holdout"]["band"]["guaranteed"] is False
    assert all(p["predicted_kw"] is not None and 0 <= p["lower_kw"] <= p["predicted_kw"] <= p["upper_kw"] for p in result["points"])
    assert result["model"]["calendar_timezone"] == "Asia/Shanghai"
    assert result["provenance"]["external_features"] == []
    assert result["provenance"]["dispatch_performed"] is False
    assert fixture.db.scalar(select(func.count()).select_from(Command)) == 0
    json.dumps(result, allow_nan=False)


def test_constant_zero_is_known_zero_and_baseline_wins_tie(fixture):
    add_history(fixture, power=lambda _: 0)
    result = run(fixture, horizon_hours=72)
    assert result["model"]["trained"]
    assert result["method"] == "seasonal_naive"
    assert result["model"]["selection_reason"] == "baseline_equal_or_better_on_validation"
    assert result["mae_kw"] == 0
    assert all(scale > 0 for scale in result["model"]["feature_scales"])
    assert result["holdout"]["baseline_improvement_pct"] is None
    assert all(p["predicted_kw"] == p["lower_kw"] == p["upper_kw"] == 0 for p in result["points"])
    assert any("Beyond 24 hours" in w for w in result["warnings"])


def test_seasonal_baseline_can_outperform_trained_model(fixture):
    add_history(fixture, power=lambda at: 1000 + 200 * ((at.hour * 13) % 7))
    result = run(fixture)
    assert result["method"] == "seasonal_naive"
    assert result["model"]["trained"]
    assert result["mae_kw"] == 0


@pytest.mark.parametrize("kwargs", [{"campus_id": "missing"}, {"building_id": "missing"}])
def test_unknown_scope_errors(fixture, kwargs):
    with pytest.raises(DomainError) as exc:
        forecast(fixture.db, now=NOW, **kwargs)
    assert exc.value.status == 404


@pytest.mark.parametrize("horizon", [0, 73, -1, 1.5, True, "24"])
def test_horizon_validation(fixture, horizon):
    with pytest.raises(DomainError, match="integer forecast horizon"):
        forecast(fixture.db, horizon_hours=horizon, now=NOW)


def test_naive_time_rejected(fixture):
    with pytest.raises(DomainError, match="timezone"):
        forecast(fixture.db, now=NOW.replace(tzinfo=None))


def test_no_devices_and_no_data_are_unknown_not_zero(fixture):
    result = run(fixture)
    assert result["coverage"]["device_ratio"] is None
    assert result["source_mode"] == "UNKNOWN"
    add_meter(fixture)
    result = run(fixture)
    assert result["source_mode"] == "SIMULATED"
    assert result["quality"] == "insufficient_data"
    assert result["mae_kw"] is None
    assert all(p["predicted_kw"] is None for p in result["points"])


def test_short_history_does_not_pretend_to_train(fixture):
    add_history(fixture, days=3)
    result = run(fixture)
    assert result["quality"] == "insufficient_data"
    assert result["model"]["trained"] is False
    assert all(p["predicted_kw"] is None for p in result["points"])


@pytest.mark.parametrize("changes,reason", [
    ({"active_power_w": None}, "missing_or_out_of_range_power"),
    ({"active_power_w": float("inf")}, "missing_or_out_of_range_power"),
    ({"active_power_w": 10_000_001}, "missing_or_out_of_range_power"),
    ({"quality": "invalid"}, "quality_excluded"),
    ({"quality_flags": ["UNCALIBRATED"]}, "quality_excluded"),
    ({"quality_flags": {}}, "quality_excluded"),
    ({"quality_flags": None}, "quality_excluded"),
    ({"raw_payload": {"valid": True, "calibrated": False}}, "calibration_or_validity_unverified"),
    ({"raw_payload": {}}, "calibration_or_validity_unverified"),
    ({"raw_payload": {"valid": True, "calibrated": "true"}}, "calibration_or_validity_unverified"),
    ({"raw_payload": {"valid": True, "calibrated": 1}}, "calibration_or_validity_unverified"),
    ({"time_source": "received_only"}, "time_source_unverified"),
    ({"time_uncertainty_ms": None}, "time_uncertain"),
    ({"time_uncertainty_ms": 6000}, "time_uncertain"),
    ({"binding_id": None}, "binding_unverified"),
    ({"source_mode": "REAL"}, "time_source_unverified"),
])
def test_unusable_measurements_remain_unknown(fixture, changes, reason):
    add_history(fixture, changes=changes)
    result = run(fixture)
    assert result["quality"] == "insufficient_data"
    assert result["coverage"]["excluded_records_and_intervals"][reason] > 0
    assert all(p["predicted_kw"] is None for p in result["points"])
    json.dumps(result, allow_nan=False)


def test_fixed_partial_cohort_does_not_turn_bad_meter_into_zero(fixture):
    add_history(fixture, ident="good", power=lambda _: 4000)
    add_history(fixture, ident="invalid", changes={"raw_payload": {"valid": True, "calibrated": False}}, power=lambda _: 900000)
    add_history(fixture, ident="stale", shift=-timedelta(hours=2), power=lambda _: 900000)
    result = run(fixture)
    assert result["coverage"]["eligible_device_ids"] == ["good"]
    assert result["coverage"]["selected_device_count"] == 3
    assert result["coverage"]["device_ratio"] == pytest.approx(1 / 3, abs=1e-6)
    assert result["coverage"]["scope_complete"] is False
    assert result["quality"] == "partial_estimate"
    assert all(p["predicted_kw"] == 4 for p in result["points"])
    assert len(result["coverage"]["excluded_devices"]) == 2


def test_parent_child_meters_are_not_double_counted(fixture):
    parent = add_meter(fixture, "parent")
    child = add_meter(fixture, "child", parent=parent[0].circuit_id)
    add_history(fixture, parent, power=lambda _: 4000)
    add_history(fixture, child, power=lambda _: 2000)
    result = run(fixture)
    assert result["coverage"]["selected_device_ids"] == ["parent"]
    assert all(p["predicted_kw"] == 4 for p in result["points"])


def test_future_observation_and_late_future_receipt_do_not_affect_result(fixture):
    device, binding = add_history(fixture)
    before = run(fixture)
    add_history(fixture, (device, binding), days=1, shift=timedelta(days=2), changes=lambda at, seq: {"boot_epoch": "future", "active_power_w": 9_999_999})
    add_history(fixture, (device, binding), days=1, changes=lambda at, seq: {"boot_epoch": "late", "received_at": NOW + HOUR, "active_power_w": 9_999_999})
    after = run(fixture)
    assert after["points"] == before["points"]
    assert after["holdout"] == before["holdout"]
    assert after["model"] == before["model"]


HOUR = timedelta(hours=1)


def test_both_event_and_receipt_times_gate_each_backtest_origin():
    times = [NOW - i * HOUR for i in range(80)]
    series = {t: 1.0 for t in times}
    availability = {t: t for t in times}
    availability[NOW - 30 * HOUR] = NOW
    history = _available_history(series, availability, NOW - 24 * HOUR, timedelta(),)
    assert NOW - 30 * HOUR not in history
    assert NOW - 24 * HOUR in history
    assert NOW - 23 * HOUR not in history


def test_recursive_daily_holdout_does_not_read_future_actuals():
    origin = NOW - 24 * HOUR
    series = {NOW - i * HOUR: 10 + i / 100 for i in range(240)}
    available = {t: t for t in series}
    before, errors = _backtest(series, available, origin, NOW, timedelta(), timezone.utc)
    changed = {t: v if t <= origin else v + 1000 for t, v in series.items()}
    after, changed_errors = _backtest(changed, available, origin, NOW, timedelta(), timezone.utc)
    assert before["sample_count"] == after["sample_count"] == 24
    for method in errors:
        assert changed_errors[method] == pytest.approx([error - 1000 for error in errors[method]])


def test_insertion_order_does_not_change_time_ordered_training(fixture):
    device, binding = add_history(fixture)
    before = run(fixture)
    records = [dict(row._mapping) for row in fixture.db.execute(select(Telemetry.__table__))]
    fixture.db.execute(delete(Telemetry))
    fixture.db.commit()
    for row in records:
        row.pop("id")
    fixture.db.execute(insert(Telemetry), list(reversed(records)))
    fixture.db.commit()
    after = run(fixture)
    assert before["points"] == after["points"]
    assert before["holdout"] == after["holdout"]
    assert before["model"]["standardized_coefficients"] == after["model"]["standardized_coefficients"]


def test_gaps_are_not_interpolated_across_or_treated_as_zero(fixture):
    add_history(fixture, power=lambda _: 2000)
    fixture.db.execute(delete(Telemetry).where(Telemetry.observed_at > NOW - 100 * HOUR, Telemetry.observed_at < NOW - 96 * HOUR))
    fixture.db.commit()
    result = run(fixture)
    assert result["coverage"]["hour_ratio"] < 1
    assert result["coverage"]["excluded_records_and_intervals"]["coverage_gap"] > 0
    assert all(p["predicted_kw"] == 2 for p in result["points"])


def test_missing_recent_lags_leave_unknown_points(fixture):
    add_history(fixture)
    fixture.db.execute(delete(Telemetry).where(Telemetry.observed_at > NOW - 2 * HOUR, Telemetry.observed_at < NOW))
    fixture.db.commit()
    result = run(fixture)
    assert result["quality"] == "insufficient_data"
    assert any(p["predicted_kw"] is None for p in result["points"])


def test_outlier_cannot_create_nonfinite_or_negative_output(fixture):
    add_history(fixture, changes=lambda at, seq: {"active_power_w": 9_999_999} if seq == 430 else {})
    result = run(fixture)
    assert result["model"]["trained"]
    assert all(p["predicted_kw"] is not None and math.isfinite(p["predicted_kw"]) and p["predicted_kw"] >= 0 for p in result["points"])
    assert result["model"]["prediction_upper_cap_kw"] < 100
    json.dumps(result, allow_nan=False)


def test_negative_power_is_explicit_import_only_not_negative_demand(fixture):
    add_history(fixture, power=lambda _: -2000)
    result = run(fixture)
    assert all(p["predicted_kw"] == 0 for p in result["points"])
    assert result["provenance"]["reverse_power_samples"] > 0
    assert "export_not_forecast" in result["provenance"]["reverse_power"]
    assert _positive_area(-1000, 1000, 3600) == 900000
    assert _positive_area(1000, -1000, 3600) == 900000


@pytest.mark.parametrize("mode", ["SIMULATED", "REPLAYED", "REAL"])
def test_source_labels_are_never_promoted_to_real(fixture, mode):
    device = add_meter(fixture, mode=mode)
    add_history(fixture, device)
    result = run(fixture)
    assert result["source_mode"] == mode
    assert result["provenance"]["training_data"] == mode
    assert result["provenance"]["real_campus_accuracy_claim"] is False
    assert result["provenance"]["measured_savings_claim"] is False
    if mode != "SIMULATED":
        assert result["quality"] == "insufficient_data", "Half-hour samples must not masquerade as continuous live telemetry"
        assert result["coverage"]["excluded_records_and_intervals"]["coverage_gap"] > 0


def test_real_cadence_can_train_but_does_not_claim_deployment_accuracy(fixture):
    device = add_meter(fixture, mode="REAL")
    add_history(fixture, device, days=8, step_seconds=30, power=lambda _: 1000)
    result = run(fixture)
    assert result["source_mode"] == "REAL"
    assert result["model"]["trained"]
    assert result["quality"] == "baseline_estimate"
    assert result["provenance"]["real_campus_accuracy_claim"] is False
    assert all(p["predicted_kw"] == 1 for p in result["points"])


def test_aggregate_row_budget_fails_explicitly_without_partial_training(fixture, monkeypatch):
    add_history(fixture)
    monkeypatch.setattr(forecasting_module, "MAX_AGGREGATE_ROWS", 100)
    result = run(fixture)
    assert result["coverage"]["aggregated_rows"] == 101
    assert result["coverage"]["source_records"] is None
    assert result["model"]["selection_reason"] == "aggregate_row_budget_exceeded"
    assert not result["model"]["trained"]
    assert all(p["predicted_kw"] is None for p in result["points"])


def test_binding_dates_are_checked_not_just_current_registry(fixture):
    device, binding = add_history(fixture)
    binding.valid_from = NOW - 2 * HOUR
    fixture.db.commit()
    result = run(fixture)
    assert not result["model"]["trained"]
    assert result["coverage"]["excluded_records_and_intervals"]["binding_unverified"] > 0


def test_non_aligned_half_hour_samples_keep_truthful_receipt_cutoffs(fixture):
    add_history(fixture, shift=-timedelta(minutes=17))
    result = run(fixture)
    assert result["coverage"]["hour_ratio"] > .98
    assert result["holdout"] is not None
    # At exact-hour issue times the current hour is unavailable until 13 minutes
    # later. A disclosed one-hour forecast bridge uses no unseen observations.
    assert result["quality"] == "partial_estimate"
    assert result["model"]["bridge_hours"] == 1
    assert result["holdout"]["sample_count"] == 47
    assert all(p["predicted_kw"] is not None for p in result["points"])
    later = forecast(fixture.db, campus_id="campus", building_id="building", now=NOW + timedelta(minutes=20))
    assert later["model"]["trained"]
    assert later["holdout"]["sample_count"] >= 24


def test_scopes_do_not_mix_other_building_history(fixture):
    add_history(fixture, power=lambda _: 4000)
    other = add_meter(fixture, "other", building="other-building")
    add_history(fixture, other, power=lambda _: 9000)
    result = run(fixture)
    assert result["coverage"]["selected_device_ids"] == ["meter"]
    assert all(p["predicted_kw"] == 4 for p in result["points"])
    campus = forecast(fixture.db, campus_id="campus", now=NOW)
    assert campus["coverage"]["selected_device_count"] == 2
    assert all(p["predicted_kw"] == 13 for p in campus["points"])


def test_source_version_changes_are_not_bridged(fixture):
    add_history(fixture, changes=lambda at, seq: {"source_version": "version-after" if at >= NOW - 4 * HOUR else "version-before"})
    result = run(fixture)
    assert result["coverage"]["excluded_records_and_intervals"]["identity_or_source_boundary"] == 1
    assert result["coverage"]["hour_ratio"] < 1
    assert result["provenance"]["source_versions"] == ["version-after", "version-before"]


def test_forecast_does_not_write_model_or_control_state(fixture):
    add_history(fixture)
    counts = {table.name: fixture.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}
    result = run(fixture)
    assert result["model"]["trained"]
    assert not fixture.db.new and not fixture.db.dirty and not fixture.db.deleted
    assert counts == {table.name: fixture.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}


@pytest.mark.parametrize("scenario", ["normal", "off_hour", "fractional_boundary", "clock_ahead", "delayed", "gaps", "invalid", "boundaries", "reverse", "uint64"])
def test_sql_hour_aggregation_matches_python_reference(fixture, scenario):
    from app.accounting import selected_devices
    from app.forecasting import _hourly_rows, _read_hourly_sql
    def changes(at, seq):
        if scenario == "clock_ahead":
            return {"received_at": at - timedelta(seconds=3)}
        if scenario == "delayed" and seq % 31 == 0:
            return {"received_at": at + 7 * HOUR}
        if scenario == "invalid" and seq % 31 == 0:
            return {"raw_payload": {"valid": True, "calibrated": False}}
        if scenario == "boundaries":
            return {"source_version": "v1" if seq < 401 else "v2", "boot_epoch": "b1" if seq < 311 else "b2"}
        if scenario == "uint64":
            return {"sample_seq": str(2 ** 64 - 1000 + seq)}
        return {}
    device, binding = add_history(fixture, shift=-timedelta(minutes=17, microseconds=123456) if scenario == "off_hour" else -timedelta(microseconds=1) if scenario == "fractional_boundary" else timedelta(),
                                 power=(lambda at: 2000 * math.sin(at.timestamp() / 1200)) if scenario == "reverse" else None, changes=changes)
    if scenario == "gaps":
        fixture.db.execute(delete(Telemetry).where(Telemetry.observed_at > NOW - 100 * HOUR, Telemetry.observed_at < NOW - 96 * HOUR))
        fixture.db.commit()
    devices = selected_devices(fixture.db, "campus", "building", start=NOW, end=NOW)
    rows = fixture.db.scalars(select(Telemetry).where(Telemetry.observed_at <= NOW, Telemetry.received_at <= NOW).order_by(Telemetry.observed_at, Telemetry.id)).all()
    reference = _hourly_rows(rows, {d.id: d for d in devices}, {binding.id: binding}, NOW)
    actual, metadata = _read_hourly_sql(fixture.db, devices, NOW - timedelta(days=21), NOW, "campus", "building")
    assert metadata["source_records"] == len(rows)
    assert metadata["reader"] == "sql_window_hour_aggregation"
    assert actual[1:] == reference[1:]
    assert actual[0].keys() == reference[0].keys()
    for ident in reference[0]:
        assert actual[0][ident] == pytest.approx(reference[0][ident], rel=1e-10, abs=1e-9)


def test_core_hour_query_preserves_immutable_campus_authorization(fixture):
    from app.forecasting import _read_hourly_sql
    from app.accounting import selected_devices
    device, binding = add_history(fixture, power=lambda _: 1000)
    fixture.db.add(Campus(id="secret-campus", name="Other scope", source="test"))
    fixture.db.flush()
    secret = Binding(device_id=device.id, campus_id="secret-campus", circuit_id=device.circuit_id, valid_from=NOW - timedelta(days=20), valid_to=NOW - HOUR, actor="test", reason="Historical other campus")
    fixture.db.add(secret)
    fixture.db.flush()
    fixture.db.execute(update(Telemetry).where(Telemetry.observed_at < NOW - HOUR).values(campus_id="secret-campus", building_id=None, binding_id=secret.id))
    fixture.db.commit()
    fixture.db.info["campus_ids"] = ["campus"]
    devices = selected_devices(fixture.db, start=NOW, end=NOW)
    actual, metadata = _read_hourly_sql(fixture.db, devices, NOW - timedelta(days=21), NOW)
    assert metadata["source_records"] == 3
    assert sum(len(hours) for hours in actual[0].values()) == 1


@pytest.mark.skipif(not os.environ.get("FORECAST_SCALE_METERS"), reason="opt-in exclusive native PostgreSQL scale benchmark")
def test_high_cadence_campus_sql_scaling(fixture, monkeypatch):
    """Run only in an exclusive load-test window; all records are synthetic replay.

    FORECAST_TEST_POSTGRES_URL must point to a disposable native test database.
    Each run uses its own random schema; FORECAST_KEEP_SCHEMA=1 retains it.
    FORECAST_SCALE_METERS=136 and FORECAST_SCALE_DAYS=8 produce 3,133,576
    observations without Python row lists. FORECAST_SCALE_READER=projection
    measures cold rebuild, warm analysis and clock-injected HTTP cache hits.
    """
    from time import perf_counter
    import resource
    from sqlalchemy import literal, literal_column, true
    from app.db import UTCDateTime
    meters = int(os.environ["FORECAST_SCALE_METERS"])
    days = int(os.environ.get("FORECAST_SCALE_DAYS", "8"))
    reader = os.environ.get("FORECAST_SCALE_READER", "sql")
    assert reader in {"sql", "projection"}
    assert 10 <= meters <= 136 and 8 <= days <= 14
    if fixture.db.bind.dialect.name != "postgresql":
        pytest.skip("large-source generation requires disposable PostgreSQL")
    from app.models import CarbonFactor, Tariff
    for index in range(meters):
        building_id = ["building", "other-building"][index] if index < 2 else f"scale-building-{index:03}"
        if index >= 2:
            fixture.db.add(Building(id=building_id, campus_id="campus", name=f"Synthetic benchmark building {index}", source="synthetic-scale-test"))
            fixture.db.flush()
        add_meter(fixture, f"scale-{index:03}", mode="REPLAYED", building=building_id)
    fixture.db.add(CarbonFactor(id="synthetic-replay-factor", name="Synthetic replay factor, not an official campus factor",
                   region="SYNTHETIC_TEST", year=NOW.year, kg_co2e_per_kwh=.55, valid_from=NOW - timedelta(days=days + 1),
                   valid_to=NOW + timedelta(days=1), source_url="https://example.invalid/synthetic-benchmark-factor", source_mode="REPLAYED", version=1))
    fixture.db.add(Tariff(id="synthetic-replay-tariff", name="Synthetic replay tariff, not a real bill", currency="CNY", rate_per_kwh=.82,
                   timezone="Asia/Shanghai", bands=[], valid_from=NOW - timedelta(days=days + 1), valid_to=NOW + timedelta(days=1),
                   source_url="https://example.invalid/synthetic-benchmark-tariff", source_mode="REPLAYED", version=1))
    fixture.db.commit()
    device, binding = Device.__table__, Binding.__table__
    target = Telemetry.__table__
    columns = ["device_id", "boot_epoch", "sample_seq", "payload_hash", "raw_payload", "observed_at", "received_at", "time_source",
               "time_uncertainty_ms", "active_power_w", "quality", "quality_flags", "source_mode", "source_version", "campus_id", "building_id", "circuit_id", "binding_id",
               "voltage_v", "current_a", "energy_import_wh", "energy_export_wh"]
    for day in range(days):
        first, last = day * 2880 + (1 if day else 0), (day + 1) * 2880
        series = func.generate_series(first, last).table_valued("seq").render_derived()
        at = literal(NOW - timedelta(days=days), type_=UTCDateTime()) + series.c.seq * literal_column("interval '30 seconds'")
        source = select(device.c.id, literal("synthetic-scale"), cast(series.c.seq, String), literal("synthetic-test-not-measured"),
                        literal({"valid": True, "calibrated": True, "synthetic": True, "energy_status": "known", "energy_uncertain_intervals": 0}, type_=target.c.raw_payload.type), at, at,
                        literal("reconstructed"), literal(0.0), 1000 + 250 * func.sin(series.c.seq * 2 * math.pi / 2880),
                        literal("good"), literal([], type_=target.c.quality_flags.type), literal("REPLAYED"), literal("synthetic-scale-v1"),
                        device.c.campus_id, device.c.building_id, device.c.circuit_id, binding.c.id, literal(230.0),
                        (1000 + 250 * func.sin(series.c.seq * 2 * math.pi / 2880)) / 230,
                        series.c.seq * (1000 / 120) + (250 * 24 / (2 * math.pi)) * (1 - func.cos(series.c.seq * 2 * math.pi / 2880)), literal(0.0)
                        ).select_from(device.join(binding, binding.c.device_id == device.c.id).join(series, true()))
        fixture.db.execute(target.insert().from_select(columns, source))
        fixture.db.commit()
        print(f"Synthetic replay inserted: day {day + 1}/{days}, {meters} meters", flush=True)
    newest = select(target.c.id).where(target.c.device_id == device.c.id).order_by(target.c.observed_at.desc(), target.c.id.desc()).limit(1).correlate(device).scalar_subquery()
    fixture.db.execute(update(Device).values(latest_telemetry_id=newest, last_seen_at=NOW))
    fixture.db.commit()
    expected_records = meters * (days * 2880 + 1)
    factory = make_session_factory(fixture.db.bind)
    if reader == "projection":
        from app.projection import queue_history, rebuild_one_batch, pending_count
        from app.models import ForecastHourRevision
        started = perf_counter()
        queue_history(fixture.db, now=NOW); fixture.db.commit()
        batches = 0
        while rebuild_one_batch(factory, now=NOW):
            batches += 1
            if batches % 100 == 0:
                print(f"Projection batches completed: {batches}", flush=True)
        assert pending_count(fixture.db, list(fixture.db.scalars(select(Device.id))), NOW, include_failed=True) == 0
        print(json.dumps({"stage": "cold_projection_rebuild", "seconds": round(perf_counter() - started, 3),
                          "source_records": expected_records, "revision_rows": fixture.db.scalar(select(func.count()).select_from(ForecastHourRevision)), "batches": batches}), flush=True)
    results = []
    for iteration in range(2):
        started = perf_counter()
        result = forecast(fixture.db, campus_id="campus", now=NOW, reader=reader)
        elapsed = perf_counter() - started
        results.append({"iteration": iteration, "reader": reader, "as_of": NOW.isoformat(), "seconds": round(elapsed, 3), "source_records": expected_records,
                        "aggregated_rows": result["coverage"]["aggregated_rows"], "meters": meters, "method": result["method"],
                        "quality": result["quality"], "source_mode": result["source_mode"], "python_peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)})
        assert result["coverage"]["source_records"] == (expected_records if reader == "sql" else None)
        assert expected_records > 200_000
        assert result["coverage"]["aggregated_rows"] < forecasting_module.MAX_AGGREGATE_ROWS
        assert result["coverage"]["eligible_device_count"] == meters
        assert result["model"]["trained"] and all(point["predicted_kw"] is not None for point in result["points"])
        assert result["source_mode"] == "REPLAYED"
        assert not any(isinstance(value, Telemetry) for value in fixture.db.identity_map.values())
        print(json.dumps(results[-1], sort_keys=True), flush=True)
    if reader == "projection":
        from fastapi.testclient import TestClient
        from app import forecast_jobs
        from app.main import create_app
        from app.config import Settings
        from app.security import bootstrap_users
        settings = Settings(env="test", database_url=os.environ["FORECAST_TEST_POSTGRES_URL"], dev_auth=True,
                            worker_enabled=False, auto_migrate=False, seed_demo=False)
        bootstrap_users(fixture.db, settings)
        application = create_app(settings)
        unused_engine = application.state.engine
        application.state.engine = fixture.db.bind
        application.state.session_factory = factory
        # Only the forecasting clock is injected; authentication remains real-time.
        monkeypatch.setattr(forecast_jobs, "utcnow", lambda: NOW)
        client = TestClient(application)
        try:
            assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "development-only"}).status_code == 200
            path = "/api/v1/forecasts?campus_id=campus&horizon_hours=24"
            queued = client.get(path)
            assert queued.status_code == 200 and queued.json()["data"]["evaluation"]["status"] == "queued"
            started = perf_counter()
            assert forecast_jobs.evaluate_one(factory, settings, now=NOW)
            print(json.dumps({"stage": "background_model_evaluation", "seconds": round(perf_counter() - started, 3)}), flush=True)
            def forbidden(*args, **kwargs):
                raise AssertionError("Warm HTTP cache hits must not fit or backtest")
            monkeypatch.setattr(forecasting_module, "_fit", forbidden)
            timings = []
            for _ in range(5):
                started = perf_counter(); response = client.get(path); timings.append(perf_counter() - started)
                assert response.status_code == 200
                body = response.json()["data"]
                assert body["evaluation"]["cached"] and body["evaluation"]["status"] == "ready"
                assert body["model"]["trained"] and all(point["predicted_kw"] is not None for point in body["points"])
            print(json.dumps({"stage": "warm_http_cache", "as_of": NOW.isoformat(), "seconds": [round(value, 4) for value in timings],
                              "maximum_seconds": round(max(timings), 4), "no_request_time_training": True}), flush=True)
        finally:
            client.close(); unused_engine.dispose()


@pytest.mark.parametrize("offset_us", [-1, 1, 999499, 999500, 999999])
def test_sql_epoch_preserves_fractional_second_boundaries(fixture, offset_us):
    from sqlalchemy import literal
    from app.db import UTCDateTime
    from app.forecasting import _sql_epoch
    at = NOW + timedelta(microseconds=offset_us)
    value = fixture.db.scalar(select(_sql_epoch(literal(at, type_=UTCDateTime()), fixture.db.bind.dialect.name)))
    assert value == pytest.approx(at.timestamp(), rel=0, abs=1e-6)


def test_interpolation_observation_time_gates_historical_availability(fixture):
    from app.accounting import selected_devices
    from app.forecasting import _read_hourly_sql
    add_history(fixture, shift=-timedelta(minutes=17), changes=lambda at, seq: {"received_at": at - timedelta(seconds=3)})
    devices = selected_devices(fixture.db, "campus", "building", start=NOW, end=NOW)
    aggregated, _ = _read_hourly_sql(fixture.db, devices, NOW - timedelta(days=21), NOW, "campus", "building")
    hourly, availability = aggregated[:2]
    hour = NOW - 24 * HOUR
    assert availability["meter"][hour] == hour + timedelta(minutes=13)
    history = _available_history(hourly["meter"], availability["meter"], hour, timedelta(minutes=12, seconds=58))
    assert hour not in history, "Receiving a future-stamped point early cannot make it available before its observed time"
    assert hour - HOUR in history


@pytest.mark.parametrize("scenario", ["empty", "populated", "insufficient", "mixed", "stale", "row_cap"])
def test_runtime_response_schema_covers_forecast_branches(fixture, monkeypatch, scenario):
    from app.responses import ForecastResponse
    if scenario == "mixed":
        add_history(fixture, ident="simulated", days=8, power=lambda _: 1000)
        replay = add_meter(fixture, "replayed", mode="REPLAYED")
        add_history(fixture, replay, days=8, step_seconds=30, power=lambda _: 2000)
    elif scenario != "empty":
        add_history(fixture, days=3 if scenario == "insufficient" else 14,
                    shift=-2 * HOUR if scenario == "stale" else timedelta())
    if scenario == "row_cap":
        monkeypatch.setattr(forecasting_module, "MAX_AGGREGATE_ROWS", 100)
    result = run(fixture)
    parsed = ForecastResponse.model_validate(result)
    wire = parsed.model_dump(mode="json")
    json.dumps(wire, allow_nan=False)
    assert wire["quality"] == result["quality"]
    assert wire["source_mode"] == result["source_mode"]
    assert len(wire["points"]) == 24
    if scenario == "mixed":
        assert parsed.source_mode == "MIXED" and parsed.model.trained
        assert parsed.coverage.eligible_device_count == 2
    if scenario == "row_cap":
        assert parsed.coverage.source_records is None
        assert parsed.model.selection_reason == "aggregate_row_budget_exceeded"


def project_hours(fixture, *, days=14, as_of=NOW, devices=None):
    from app.forecasting import rebuild_forecast_hours
    devices = devices or list(fixture.db.scalars(select(Device)))
    hours = [NOW - i * HOUR for i in range(days * 24 - 1, -1, -1)]
    for device in devices:
        for offset in range(0, len(hours), 24):
            rebuild_forecast_hours(fixture.db, device.id, hours[offset:offset + 24], as_of=as_of)
    fixture.db.commit()


def test_projection_forecast_matches_sql_oracle_and_is_read_only(fixture):
    from app.responses import ForecastResponse
    from app.models import ForecastHourRevision
    add_history(fixture)
    oracle = run(fixture)
    project_hours(fixture)
    count = fixture.db.scalar(select(func.count()).select_from(ForecastHourRevision))
    result = run(fixture, reader="projection")
    assert result["provenance"]["reader"] == "persistent_hour_revisions"
    assert result["points"] == oracle["points"]
    assert result["holdout"] == oracle["holdout"]
    assert result["coverage"]["eligible_device_count"] == 1
    assert result["coverage"]["source_records"] is None
    assert fixture.db.scalar(select(func.count()).select_from(ForecastHourRevision)) == count
    assert not fixture.db.new and not fixture.db.dirty
    ForecastResponse.model_validate(result)


def test_projection_is_explicitly_pending_without_raw_fallback(fixture, monkeypatch):
    add_history(fixture)
    def forbidden(*args, **kwargs):
        raise AssertionError("Projection requests must not run the raw SQL oracle")
    monkeypatch.setattr(forecasting_module, "_read_hourly_sql", forbidden)
    result = run(fixture, reader="projection")
    assert result["model"]["selection_reason"] == "projection_pending"
    assert result["quality"] == "insufficient_data"
    assert all(point["predicted_kw"] is None for point in result["points"])


def test_projection_rebuild_is_idempotent_and_bounded(fixture, monkeypatch):
    from app.forecasting import rebuild_forecast_hours, rebuild_hour
    from app.models import ForecastHourRevision
    add_history(fixture)
    first = rebuild_hour(fixture.db, "meter", NOW - HOUR, NOW)
    fixture.db.commit()
    again = rebuild_hour(fixture.db, "meter", NOW - HOUR, NOW + HOUR)
    assert [row.id for row in first] == [row.id for row in again]
    assert first[0].data["covered_seconds"] == pytest.approx(3600)
    assert fixture.db.scalar(select(func.count()).select_from(ForecastHourRevision)) == 1
    with pytest.raises(DomainError, match="24-hour span"):
        rebuild_forecast_hours(fixture.db, "meter", [NOW - 25 * HOUR, NOW], as_of=NOW)
    monkeypatch.setattr(forecasting_module, "MAX_REBUILD_SOURCE_ROWS", 1)
    with pytest.raises(DomainError) as error:
        rebuild_hour(fixture.db, "meter", NOW, NOW)
    assert error.value.code == "forecast_rebuild_budget_exceeded"
    assert fixture.db.scalar(select(func.count()).select_from(ForecastHourRevision)) == 1


def test_late_invalidating_fact_preserves_old_as_of_revision(fixture):
    from app.accounting import selected_devices
    from app.forecasting import rebuild_hour, _read_hourly_projection, _value_at
    from app.models import ForecastHourRevision
    device, binding = add_history(fixture, power=lambda _: 1000, changes=lambda at, seq: {"sample_seq": str(seq * 2)})
    target = NOW - 72 * HOUR
    old = rebuild_hour(fixture.db, device.id, target, NOW)[0]
    fixture.db.commit()
    old_id, old_data = old.id, json.loads(json.dumps(old.data))
    late_at, received = target - timedelta(minutes=45), NOW + timedelta(seconds=10)
    predecessor = fixture.db.scalar(select(Telemetry).where(Telemetry.device_id == device.id, Telemetry.observed_at < late_at).order_by(Telemetry.observed_at.desc()).limit(1))
    raw = dict(device_id=device.id, boot_epoch="epoch", sample_seq=str(int(predecessor.sample_seq) + 1), observed_at=late_at, received_at=received,
               active_power_w=9999.0, quality="invalid", quality_flags=["MEASUREMENT_INVALID"], time_source="simulated", time_uncertainty_ms=0.0,
               raw_payload={"valid": False, "calibrated": True}, payload_hash="late-synthetic", source_mode="SIMULATED", source_version="synthetic-test-v1",
               binding_id=binding.id, campus_id="campus", building_id="building", circuit_id=device.circuit_id)
    fixture.db.execute(insert(Telemetry), [raw]); fixture.db.commit()
    new = rebuild_hour(fixture.db, device.id, target, received)[0]
    fixture.db.commit()
    assert new.id != old_id and new.data["complete_kw"] is None
    assert new.available_at == received
    assert fixture.db.get(ForecastHourRevision, old_id).data == old_data
    devices = selected_devices(fixture.db, "campus", "building", start=received, end=received)
    evidence, _ = _read_hourly_projection(fixture.db, devices, NOW - timedelta(days=21), received, "campus", "building")
    values, availability = evidence[:2]
    assert _value_at(values[device.id], availability[device.id], target, target + HOUR) == 1
    assert _value_at(values[device.id], availability[device.id], target, received) is None
    assert len(fixture.db.scalars(select(ForecastHourRevision)).all()) == 2


def test_projection_hour_interpolation_keeps_observed_and_received_cutoffs(fixture):
    from app.forecasting import rebuild_hour
    add_history(fixture, shift=-timedelta(minutes=17), changes=lambda at, seq: {"received_at": at - timedelta(seconds=3)})
    target = NOW - HOUR
    row = rebuild_hour(fixture.db, "meter", target, NOW)[0]
    assert row.available_at == target + timedelta(minutes=13)
    assert row.data["complete_kw"] is not None


def test_projection_rebuild_rejects_scoped_session(fixture):
    from app.forecasting import rebuild_hour
    add_history(fixture)
    fixture.db.info["campus_ids"] = ["campus"]
    with pytest.raises(DomainError) as error:
        rebuild_hour(fixture.db, "meter", NOW, NOW)
    assert error.value.code == "forecast_rebuild_scope"


def test_forecast_template_is_pure_and_schema_valid():
    from app.forecasting import forecast_template
    from app.responses import ForecastResponse
    result = forecast_template([SimpleNamespace(id="meter", source_mode="SIMULATED")], "campus", "building", 12, NOW)
    assert len(result["points"]) == 12
    assert result["coverage"]["source_records"] is None
    assert not result["model"]["trained"]
    ForecastResponse.model_validate(result)


@pytest.mark.parametrize("scenario", ["zero", "negative", "missing_power", "uncalibrated", "off_hour", "source_boundary", "gap"])
def test_projection_preserves_data_quality_and_source_semantics(fixture, scenario):
    power = (lambda _: 0) if scenario == "zero" else (lambda _: -2000) if scenario == "negative" else None
    def changes(at, seq):
        if scenario == "missing_power":
            return {"active_power_w": None}
        if scenario == "uncalibrated":
            return {"raw_payload": {"valid": True, "calibrated": False}}
        if scenario == "source_boundary":
            return {"source_version": "v1" if at < NOW - 100 * HOUR else "v2"}
        return {}
    add_history(fixture, power=power, changes=changes, shift=-timedelta(minutes=17) if scenario == "off_hour" else timedelta())
    if scenario == "gap":
        fixture.db.execute(delete(Telemetry).where(Telemetry.observed_at > NOW - 100 * HOUR, Telemetry.observed_at < NOW - 96 * HOUR))
        fixture.db.commit()
    oracle = run(fixture)
    project_hours(fixture)
    result = run(fixture, reader="projection")
    assert result["method"] == oracle["method"]
    assert result["quality"] == oracle["quality"]
    assert result["points"] == oracle["points"]
    assert result["holdout"] == oracle["holdout"]
    assert result["provenance"]["dispatch_performed"] is False
    if scenario == "negative":
        assert result["provenance"]["reverse_power_samples"] == 14 * 48


def test_projection_keeps_historical_campus_evidence_out_of_other_scope(fixture):
    from app.forecasting import rebuild_forecast_hours, _read_hourly_projection
    from app.accounting import selected_devices
    from app.models import ForecastHourRevision
    device, binding = add_history(fixture, power=lambda _: 1000)
    fixture.db.add(Campus(id="other-campus", name="Other fixture", source="test")); fixture.db.flush()
    other = Binding(device_id=device.id, campus_id="other-campus", circuit_id=device.circuit_id,
                    valid_from=NOW - timedelta(days=20), valid_to=NOW - HOUR, actor="test", reason="Historical other scope")
    fixture.db.add(other); fixture.db.flush()
    fixture.db.execute(update(Telemetry).where(Telemetry.observed_at < NOW - HOUR).values(campus_id="other-campus", building_id=None, binding_id=other.id, source_version="private-other-version"))
    fixture.db.commit()
    rebuild_forecast_hours(fixture.db, device.id, [NOW - HOUR, NOW], as_of=NOW); fixture.db.commit()
    assert fixture.db.scalar(select(func.count()).select_from(ForecastHourRevision).where(ForecastHourRevision.campus_id == "other-campus"))
    fixture.db.info["campus_ids"] = ["campus"]
    devices = selected_devices(fixture.db, start=NOW, end=NOW)
    data, metadata = _read_hourly_projection(fixture.db, devices, NOW - timedelta(days=21), NOW)
    assert set(data[0][device.id]) == {NOW}
    assert "private-other-version" not in data[4][device.id]


def test_projection_same_time_corrections_use_source_watermark_before_row_id(fixture):
    from app.forecasting import rebuild_hour, _read_hourly_projection, _value_at
    from app.accounting import selected_devices
    from app.models import ForecastHourRevision
    add_history(fixture, power=lambda _: 1000)
    target = NOW - 72 * HOUR
    base = rebuild_hour(fixture.db, "meter", target, NOW)[0]; fixture.db.commit()
    for marker, watermark, value in [("new-facts", 10000, 2.0), ("late-old-computation", 9000, 3.0)]:
        data = json.loads(json.dumps(base.data)); data.update(import_area_w_seconds=value * 3_600_000, complete_kw=value)
        fixture.db.add(ForecastHourRevision(device_id=base.device_id, campus_id=base.campus_id, building_id=base.building_id,
                       circuit_id=base.circuit_id, source_mode=base.source_mode, scope_key=base.scope_key, hour_end=target,
                       available_at=NOW - HOUR, computed_at=NOW, source_watermark=watermark, content_hash=marker, data=data))
        fixture.db.commit()
    devices = selected_devices(fixture.db, "campus", "building", start=NOW, end=NOW)
    evidence, _ = _read_hourly_projection(fixture.db, devices, NOW - timedelta(days=21), NOW, "campus", "building")
    values, availability = evidence[:2]
    assert _value_at(values["meter"], availability["meter"], target, NOW) == 2
    assert _value_at(values["meter"], availability["meter"], target, target + HOUR) == 1


def test_current_head_eligibility_expires_behind_bad_latest_pointer(fixture):
    from app.forecasting import forecast_head_evidence
    from app.accounting import selected_devices
    device, binding = add_history(fixture)
    row = Telemetry(device_id=device.id, boot_epoch="epoch", sample_seq="673", observed_at=NOW + timedelta(minutes=1), received_at=NOW + timedelta(minutes=1),
                    active_power_w=9999, quality="invalid", quality_flags=["MEASUREMENT_INVALID"], time_source="simulated", time_uncertainty_ms=0.0,
                    raw_payload={"valid": False, "calibrated": True}, payload_hash="test-bad-head", source_mode="SIMULATED", source_version="synthetic-test-v1",
                    binding_id=binding.id, campus_id="campus", building_id="building", circuit_id=device.circuit_id)
    fixture.db.add(row); fixture.db.flush(); device.latest_telemetry_id = row.id; fixture.db.commit()
    devices = selected_devices(fixture.db, "campus", "building", start=NOW, end=NOW)
    before, _ = forecast_head_evidence(fixture.db, devices, NOW + timedelta(minutes=30), "campus", "building")
    after, _ = forecast_head_evidence(fixture.db, devices, NOW + timedelta(seconds=3601), "campus", "building")
    assert before == {device.id: NOW}
    assert after == {}
