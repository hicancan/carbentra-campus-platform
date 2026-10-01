"""Bounded, read-only hourly import-load forecasting; no external model service.

A fixed, explicitly reported cohort is drawn from accounting's current meter
antichain. Only calibrated, time-attributed, good-quality adjacent observations
inside their immutable placement are integrated. Import is the positive part of
linearly interpolated signed power; export is not forecast. Missing intervals
remain missing, and an aggregate hour requires every cohort meter's whole hour.

A deterministic standardized ridge regression learns lag/calendar features from
at most 21 days / 100,000 hour-revision or SQL-aggregate rows. Two expanding-origin validation
blocks select it against a 24-hour seasonal-naive baseline; later, disjoint
holdout blocks assess both. Each block recursively predicts without seeing that
block's actuals. Observation AND receipt times gate every training origin. A maximum one-hour
trailing availability gap may be bridged by explicit model predictions, never
by invented measurements; older anchors fail closed.
After selection, the model is refit using only data available at request time.
Bands are empirical holdout absolute-error quantiles, not confidence guarantees.
Simulation/replay provenance is retained; no occupancy, weather, savings or
physical-control claims are inferred. forecast() is read-only and explicitly
selects the SQL oracle or persistent revisions; it never falls back between them.
Background rebuild helpers append idempotent derived evidence without committing.
Raw telemetry remains authoritative; HTTP snapshot/cache handling lives elsewhere.
"""
from collections import Counter, defaultdict, namedtuple
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from statistics import mean
from types import SimpleNamespace
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import BigInteger, Float, String, and_, case, cast, func, literal, or_, select, union_all

from .accounting import selected_devices
from .common import DomainError, payload_hash
from .db import UTCDateTime, iso, utcnow
from .models import Binding, Building, Campus, Device, Telemetry

VERSION = "hourly-import-ridge-v2"
HISTORY_DAYS = 21
MAX_AGGREGATE_ROWS = 100_000
MAX_DEVICES = 2_000
MAX_REBUILD_SOURCE_ROWS = 100_000
MAX_REBUILD_HOURS = 24
MAX_HEAD_SAMPLES = 16
MIN_HISTORY_HOURS = 168
MIN_FIT_SAMPLES = 48
MIN_SCORE_SAMPLES = 12
MIN_DEVICE_HOUR_RATIO = .80
MAX_POWER_W = 10_000_000.0
RIDGE_ALPHA = 5.0
HOUR = timedelta(hours=1)
FEATURE_NAMES = ["lag_1h_kw", "lag_24h_kw", "lag_48h_kw", "mean_previous_24h_kw",
                 "hour_sin", "hour_cos", "hour_second_sin", "hour_second_cos",
                 "weekday_sin", "weekday_cos", "weekend", "elapsed_days"]


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _round(value):
    return round(value, 6) if value is not None and math.isfinite(value) else None


def _hour(value):
    return value.replace(minute=0, second=0, microsecond=0)


def _quantile(values, probability):
    values = sorted(values)
    if not values:
        return None
    return values[min(len(values) - 1, math.ceil(probability * len(values)) - 1)]


def _mode(modes):
    modes = set(modes)
    return next(iter(modes)) if len(modes) == 1 else "MIXED" if modes else "UNKNOWN"


def _features(at, history, origin_start, tz):
    required = [at - i * HOUR for i in range(1, 25)] + [at - 48 * HOUR]
    if any(t not in history for t in required):
        return None
    local = (at - HOUR).astimezone(tz)  # Calendar of the interval's start.
    hour_angle, week_angle = 2 * math.pi * local.hour / 24, 2 * math.pi * local.weekday() / 7
    return [history[at - HOUR], history[at - 24 * HOUR], history[at - 48 * HOUR],
            mean(history[at - i * HOUR] for i in range(1, 25)),
            math.sin(hour_angle), math.cos(hour_angle), math.sin(2 * hour_angle), math.cos(2 * hour_angle),
            math.sin(week_angle), math.cos(week_angle), float(local.weekday() >= 5),
            (at - origin_start).total_seconds() / 86400]


def _solve_positive_definite(matrix, target):
    """Small Cholesky solve; ridge makes the standardized Gram matrix positive definite."""
    n = len(target)
    lower = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            remainder = matrix[i][j] - sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                if not math.isfinite(remainder) or remainder <= 0:
                    return None
                lower[i][j] = math.sqrt(remainder)
            else:
                lower[i][j] = remainder / lower[j][j]
    forward = [0.0] * n
    for i in range(n):
        forward[i] = (target[i] - sum(lower[i][j] * forward[j] for j in range(i))) / lower[i][i]
    answer = [0.0] * n
    for i in range(n - 1, -1, -1):
        answer[i] = (forward[i] - sum(lower[j][i] * answer[j] for j in range(i + 1, n))) / lower[i][i]
    return answer if all(math.isfinite(x) for x in answer) else None


def _fit(history, tz):
    if not history:
        return None
    start = min(history)
    examples = [(x, history[t]) for t in sorted(history) if (x := _features(t, history, start, tz)) is not None]
    if len(examples) < MIN_FIT_SAMPLES:
        return None
    # Fit-only robust bound limits extreme training targets and recursive extrapolation.
    # Held-out actuals are NEVER clipped or removed from error metrics.
    targets = [y for _, y in examples]
    upper = max(0.0, 3 * _quantile(targets, .95))
    features = [x for x, _ in examples]
    centers = [mean(x[j] for x in features) for j in range(len(FEATURE_NAMES))]
    scales = [max(1e-8, math.sqrt(mean((x[j] - centers[j]) ** 2 for x in features))) for j in range(len(FEATURE_NAMES))]
    target_center = mean(min(y, upper) for y in targets)
    n = len(FEATURE_NAMES)
    gram = [[RIDGE_ALPHA if i == j else 0.0 for j in range(n)] for i in range(n)]
    rhs = [0.0] * n
    for features, y in examples:
        z = [(features[j] - centers[j]) / scales[j] for j in range(n)]
        residual = min(y, upper) - target_center
        for i in range(n):
            rhs[i] += z[i] * residual
            for j in range(i + 1):
                gram[i][j] += z[i] * z[j]
    for i in range(n):
        for j in range(i):
            gram[j][i] = gram[i][j]
    coefficients = _solve_positive_definite(gram, rhs)
    if coefficients is None:
        return None
    return {"centers": centers, "scales": scales, "coefficients": coefficients, "intercept": target_center,
            "upper": upper, "start": start, "sample_count": len(examples), "trained_until": max(history)}


def _value_at(series, availability, at, issued_at):
    evidence = availability.get(at)
    if isinstance(evidence, datetime):
        return series.get(at) if evidence <= issued_at else None
    if evidence:
        for known_at, value in reversed(evidence):
            if known_at <= issued_at:
                return value
    return None


def _available_history(series, availability, origin, phase):
    issued_at = origin + phase
    return {at: value for at in availability if at <= origin
            and (value := _value_at(series, availability, at, issued_at)) is not None}


def _evidence_events(series, availability, at):
    evidence = availability.get(at)
    return [(evidence, series[at])] if isinstance(evidence, datetime) else (evidence or [])


def _combine_histories(identities, values, evidence, first_hour, origin):
    """Merge per-meter revision timelines without making missing meters zero."""
    common = set.intersection(*(set(evidence[identity]) for identity in identities))
    series, availability = {}, {}
    for at in sorted(common):
        if not first_hour <= at <= origin:
            continue
        changes = defaultdict(list)
        for identity in identities:
            for known_at, value in _evidence_events(values[identity], evidence[identity], at):
                changes[known_at].append((identity, value))
        current, history = {}, []
        for known_at, updates in sorted(changes.items()):
            current.update(updates)
            value = sum(current.values()) if len(current) == len(identities) and all(v is not None for v in current.values()) else None
            if not history or value != history[-1][1]:
                history.append((known_at, value))
        availability[at] = history
        if history and history[-1][1] is not None:
            series[at] = history[-1][1]
    return series, availability


def _predict(history, origin, hours, method, model, tz):
    values, points = dict(history), {}
    anchor = max(history, default=origin)
    gap = int((origin - anchor) / HOUR)
    if gap > 1 or gap < 0:
        return {origin + step * HOUR: None for step in range(1, hours + 1)}
    for step in range(1, hours + gap + 1):
        target = anchor + step * HOUR
        value = None
        if method == "seasonal_naive":
            value = values.get(target - 24 * HOUR)
        elif model is not None:
            features = _features(target, values, model["start"], tz)
            if features is not None:
                value = model["intercept"] + sum(c * (x - center) / scale for c, x, center, scale in
                    zip(model["coefficients"], features, model["centers"], model["scales"]))
                value = min(model["upper"], max(0.0, value)) if math.isfinite(value) else None
        if value is not None:
            values[target] = value
        if target > origin:
            points[target] = value
    return points


def _metrics(errors):
    return {"mae_kw": _round(mean(abs(x) for x in errors)) if errors else None,
            "rmse_kw": _round(math.sqrt(mean(x * x for x in errors))) if errors else None}


def _backtest(series, availability, start, end, phase, tz):
    errors = {"ridge_regression": [], "seasonal_naive": []}
    folds, origin = [], start
    while origin < end:
        steps = min(24, int((end - origin) / HOUR))
        history = _available_history(series, availability, origin, phase)
        fitted = _fit(history, tz)
        predictions = {name: _predict(history, origin, steps, name, fitted, tz) for name in errors}
        matched = 0
        for target in predictions["seasonal_naive"]:
            if target not in series or any(predictions[name][target] is None for name in errors):
                continue
            for name in errors:
                errors[name].append(predictions[name][target] - series[target])
            matched += 1
        folds.append({"issued_at": iso(origin + phase), "training_end": iso(max(history, default=None)),
                      "target_start": iso(origin + HOUR), "target_end": iso(origin + steps * HOUR), "sample_count": matched})
        origin += steps * HOUR
    expected = int((end - start) / HOUR)
    return {"start": iso(start + HOUR), "end": iso(end), "sample_count": len(errors["seasonal_naive"]),
            "expected_hours": expected, "coverage_ratio": _round(len(errors["seasonal_naive"]) / expected) if expected else None,
            "models": {name: _metrics(values) for name, values in errors.items()}, "folds": folds}, errors


def _record_reason(row, device, binding):
    if row.quality != "good" or not isinstance(row.quality_flags, list) or row.quality_flags:
        return "quality_excluded"
    if not _finite(row.active_power_w) or abs(row.active_power_w) > MAX_POWER_W:
        return "missing_or_out_of_range_power"
    raw = row.raw_payload if isinstance(row.raw_payload, dict) else {}
    if raw.get("calibrated") is not True or raw.get("valid") is not True:
        return "calibration_or_validity_unverified"
    if not _finite(row.time_uncertainty_ms) or not 0 <= row.time_uncertainty_ms <= 5000:
        return "time_uncertain"
    if row.time_source not in {"authenticated", "reconstructed", "simulated"} or (row.time_source == "simulated" and row.source_mode != "SIMULATED"):
        return "time_source_unverified"
    if row.source_mode != device.source_mode or row.source_mode not in {"SIMULATED", "REPLAYED", "REAL"}:
        return "source_mode_mismatch"
    if row.observed_at > row.received_at + timedelta(seconds=5):
        return "observation_ahead_of_receipt"
    if binding is None or binding.device_id != row.device_id or not binding.valid_from <= row.observed_at or (binding.valid_to and row.observed_at >= binding.valid_to):
        return "binding_unverified"
    if (row.campus_id, row.building_id, row.circuit_id) != (binding.campus_id, binding.building_id, binding.circuit_id) or row.circuit_id != device.circuit_id:
        return "placement_mismatch"
    try:
        if not 0 <= int(row.sample_seq) <= 2 ** 64 - 1 or str(int(row.sample_seq)) != row.sample_seq:
            return "invalid_sequence"
    except (ValueError, TypeError):
        return "invalid_sequence"
    return None


def _positive_area(a, b, seconds):
    """Integral of positive, linearly interpolated power (W seconds)."""
    if a >= 0 and b >= 0:
        return (a + b) * .5 * seconds
    if a <= 0 and b <= 0:
        return 0.0
    positive = max(a, b)
    return .5 * positive * seconds * positive / abs(b - a)


def _hourly_rows(rows, devices, bindings, now):
    """Small-fixture reference oracle for SQL parity tests; not the production reader."""
    buckets, previous, latest, reasons, versions = {}, {}, {}, Counter(), defaultdict(set)
    reverse_records = 0
    for row in rows:
        device = devices[row.device_id]
        reason = _record_reason(row, device, bindings.get(row.binding_id))
        prior, prior_reason = previous.get(row.device_id, (None, None))
        previous[row.device_id] = row, reason
        if reason:
            reasons[reason] += 1
            continue
        latest[row.device_id] = max(latest.get(row.device_id, row.observed_at), row.observed_at)
        versions[row.device_id].add(row.source_version)
        reverse_records += int(row.active_power_w < 0)
        if prior is None:
            continue
        if prior_reason:
            reasons["invalid_interval_endpoint"] += 1
            continue
        seconds = (row.observed_at - prior.observed_at).total_seconds()
        max_gap = 1800 if row.source_mode == "SIMULATED" else 30
        if seconds <= 0 or (row.boot_epoch == prior.boot_epoch and int(row.sample_seq) <= int(prior.sample_seq)):
            reasons["sequence_or_time_regression"] += 1
            continue
        if seconds > max_gap:
            reasons["coverage_gap"] += 1
            continue
        if row.boot_epoch != prior.boot_epoch or row.binding_id != prior.binding_id or row.source_version != prior.source_version:
            reasons["identity_or_source_boundary"] += 1
            continue
        start, end = prior.observed_at, row.observed_at
        while start < end:
            hour_end = _hour(start) + HOUR
            segment_end = min(end, hour_end)
            duration = (segment_end - start).total_seconds()
            left = prior.active_power_w + (row.active_power_w - prior.active_power_w) * (start - prior.observed_at).total_seconds() / seconds
            right = prior.active_power_w + (row.active_power_w - prior.active_power_w) * (segment_end - prior.observed_at).total_seconds() / seconds
            key = (row.device_id, hour_end)
            area, covered, available = buckets.get(key, (0.0, 0.0, row.received_at))
            buckets[key] = (area + _positive_area(left, right, duration), covered + duration,
                            max(available, prior.received_at, row.received_at, row.observed_at, hour_end))
            start = segment_end
    hourly, availability = defaultdict(dict), defaultdict(dict)
    for (device_id, at), (area, seconds, available) in buckets.items():
        if at <= _hour(now) and abs(seconds - 3600) < .001:
            hourly[device_id][at] = area / 3600 / 1000
            availability[device_id][at] = available
    return hourly, availability, latest, reasons, versions, reverse_records



def _sql_epoch(column, dialect):
    if dialect == "postgresql":
        return cast(func.extract("epoch", column), Float)
    # UTCDateTime stores SQLite timestamps with six fractional digits. Avoid
    # julianday's boundary rounding and strftime('%f')'s millisecond truncation.
    # Strip the fraction before strftime: some SQLite builds round .999999 up.
    stored = cast(column, String)
    return cast(func.strftime("%s", func.substr(stored, 1, 19)), Float) + func.coalesce(cast(func.substr(stored, 21, 6), Float), 0) / 1_000_000


def _read_hourly_sql(db, devices, window_start, now, campus_id=None, building_id=None):
    """One bounded-output SQL query; DB performs interval validation and integration.

    SQLite and PostgreSQL share the window/CTE arithmetic. Only epoch conversion,
    strict JSON type checks and canonical uint64 validation are dialect-specific.
    The explicit immutable-campus predicate is essential: Core aggregates do not
    rely on ORM loader criteria to enforce authorization after a device moves.
    """
    dialect = db.bind.dialect.name
    version = db.bind.dialect.server_version_info or ()
    minimum = {"sqlite": (3, 35), "postgresql": (12,)}
    if dialect not in minimum or version < minimum.get(dialect, ()):
        return None, {"failure": "unsupported_forecast_sql_dialect_or_version", "source_records": None}
    t, b, d = Telemetry.__table__, Binding.__table__, Device.__table__
    ids = [device.id for device in devices]
    # Materialize only the small identity snapshot. Evaluating a 136-way CASE
    # per observation would undermine the benefit of server-side aggregation.
    chosen = select(d.c.id.label("device_id"),
                    case({device.id: device.source_mode for device in devices}, value=d.c.id).label("expected_mode"),
                    case({device.id: device.circuit_id for device in devices}, value=d.c.id).label("expected_circuit")
                    ).where(d.c.id.in_(ids)).cte("forecast_chosen").prefix_with("MATERIALIZED")
    expected_mode, expected_circuit = chosen.c.expected_mode, chosen.c.expected_circuit
    if dialect == "sqlite":
        calibrated = and_(func.json_type(t.c.raw_payload, "$.calibrated") == "true", func.json_type(t.c.raw_payload, "$.valid") == "true")
        flags_empty = and_(func.json_type(t.c.quality_flags) == "array", func.json_array_length(t.c.quality_flags) == 0)
        sequence_valid = and_(t.c.sample_seq != "", ~t.c.sample_seq.bool_op("GLOB")("*[^0-9]*"),
                              or_(t.c.sample_seq == "0", func.substr(t.c.sample_seq, 1, 1) != "0"))
    else:
        calibrated = and_(func.json_typeof(t.c.raw_payload["calibrated"]) == "boolean", t.c.raw_payload["calibrated"].as_string() == "true",
                          func.json_typeof(t.c.raw_payload["valid"]) == "boolean", t.c.raw_payload["valid"].as_string() == "true")
        flags_empty = case((func.json_typeof(t.c.quality_flags) == "array", func.json_array_length(t.c.quality_flags)), else_=-1) == 0
        sequence_valid = t.c.sample_seq.bool_op("~")(r"^(0|[1-9][0-9]{0,19})$")
    sequence_valid = and_(sequence_valid, or_(func.length(t.c.sample_seq) < 20,
                         and_(func.length(t.c.sample_seq) == 20, t.c.sample_seq <= "18446744073709551615")))
    observed_seconds, received_seconds = _sql_epoch(t.c.observed_at, dialect), _sql_epoch(t.c.received_at, dialect)
    reason = case(
        (or_(t.c.quality != "good", ~func.coalesce(flags_empty, False)), "quality_excluded"),
        (~func.coalesce(t.c.active_power_w.between(-MAX_POWER_W, MAX_POWER_W), False), "missing_or_out_of_range_power"),
        (~func.coalesce(calibrated, False), "calibration_or_validity_unverified"),
        (~func.coalesce(t.c.time_uncertainty_ms.between(0, 5000), False), "time_uncertain"),
        (or_(~t.c.time_source.in_(["authenticated", "reconstructed", "simulated"]),
             and_(t.c.time_source == "simulated", t.c.source_mode != "SIMULATED")), "time_source_unverified"),
        (or_(t.c.source_mode != expected_mode, ~t.c.source_mode.in_(["SIMULATED", "REPLAYED", "REAL"])), "source_mode_mismatch"),
        (observed_seconds > received_seconds + 5, "observation_ahead_of_receipt"),
        (or_(b.c.id.is_(None), b.c.device_id != t.c.device_id, b.c.valid_from > t.c.observed_at,
             and_(b.c.valid_to.is_not(None), t.c.observed_at >= b.c.valid_to)), "binding_unverified"),
        (or_(t.c.campus_id.is_distinct_from(b.c.campus_id), t.c.building_id.is_distinct_from(b.c.building_id),
             t.c.circuit_id.is_distinct_from(b.c.circuit_id), t.c.circuit_id.is_distinct_from(expected_circuit)), "placement_mismatch"),
        (~func.coalesce(sequence_valid, False), "invalid_sequence"), else_=None).label("reason")
    filters = [t.c.device_id.in_(ids), t.c.observed_at >= window_start - HOUR, t.c.observed_at <= now, t.c.received_at <= now]
    if campus_id:
        filters.append(t.c.campus_id == campus_id)
    if building_id:
        filters.append(t.c.building_id == building_id)
    if db.info.get("campus_ids") is not None:
        filters.append(t.c.campus_id.in_(db.info["campus_ids"]))
    checked = select(t.c.id, t.c.device_id, t.c.observed_at, t.c.received_at, t.c.active_power_w,
                     t.c.source_mode, t.c.source_version, t.c.boot_epoch, t.c.sample_seq, t.c.binding_id,
                     observed_seconds.label("observed_seconds"), reason).select_from(t.join(chosen, chosen.c.device_id == t.c.device_id).outerjoin(b, b.c.id == t.c.binding_id)).where(*filters).cte("forecast_checked")
    lag_names = ("id", "reason", "observed_seconds", "received_at", "active_power_w", "boot_epoch", "sample_seq", "binding_id", "source_version")
    lagged = select(checked, *[func.lag(checked.c[name]).over(partition_by=checked.c.device_id,
                             order_by=(checked.c.observed_at, checked.c.id)).label("previous_" + name) for name in lag_names]).cte("forecast_lagged")
    c = lagged.c
    seconds = c.observed_seconds - c.previous_observed_seconds
    regressed = or_(func.length(c.sample_seq) < func.length(c.previous_sample_seq),
                    and_(func.length(c.sample_seq) == func.length(c.previous_sample_seq), c.sample_seq <= c.previous_sample_seq))
    interval_reason = case((c.reason.is_not(None), c.reason), (c.previous_id.is_(None), None),
        (c.previous_reason.is_not(None), "invalid_interval_endpoint"),
        (or_(seconds <= 0, and_(c.boot_epoch == c.previous_boot_epoch, regressed)), "sequence_or_time_regression"),
        (seconds > case((c.source_mode == "SIMULATED", 1800), else_=30), "coverage_gap"),
        (or_(c.boot_epoch != c.previous_boot_epoch, c.binding_id.is_distinct_from(c.previous_binding_id),
             c.source_version != c.previous_source_version), "identity_or_source_boundary"), else_=None)
    hour_number = c.previous_observed_seconds / 3600
    truncated = cast(hour_number, BigInteger)
    hour_floor = func.floor(hour_number) if dialect == "postgresql" else case((hour_number < truncated, truncated - 1), else_=truncated)
    received_availability = case((c.received_at >= c.previous_received_at, c.received_at), else_=c.previous_received_at)
    # Clock uncertainty may place an observation a few seconds after receipt.
    # Both timestamps must precede each historical issue time, including the
    # right-hand observation needed to interpolate an earlier hour boundary.
    interval_availability = case((c.observed_at > received_availability, c.observed_at), else_=received_availability)
    paired = select(lagged, seconds.label("seconds"), interval_reason.label("interval_reason"),
                    ((hour_floor + 1) * 3600).label("first_hour_end"),
                    interval_availability.label("available_at")).cte("forecast_paired")
    c = paired.c
    valid_pair = and_(c.previous_id.is_not(None), c.interval_reason.is_(None))
    segment_end = case((c.observed_seconds < c.first_hour_end, c.observed_seconds), else_=c.first_hour_end)
    first = select(c.device_id, c.previous_observed_seconds.label("start"), segment_end.label("end"), c.first_hour_end.label("hour_end"),
                   c.previous_active_power_w.label("left_power"),
                   (c.previous_active_power_w + (c.active_power_w - c.previous_active_power_w) *
                    (segment_end - c.previous_observed_seconds) / func.nullif(c.seconds, 0)).label("right_power"), c.available_at).where(valid_pair)
    second = select(c.device_id, c.first_hour_end.label("start"), c.observed_seconds.label("end"), (c.first_hour_end + 3600).label("hour_end"),
                    (c.previous_active_power_w + (c.active_power_w - c.previous_active_power_w) *
                     (c.first_hour_end - c.previous_observed_seconds) / func.nullif(c.seconds, 0)).label("left_power"),
                    c.active_power_w.label("right_power"), c.available_at).where(valid_pair, c.observed_seconds > c.first_hour_end)
    segments = union_all(first, second).cte("forecast_segments")
    c = segments.c
    duration = c.end - c.start
    positive = case((c.left_power > c.right_power, c.left_power), else_=c.right_power)
    area = case((and_(c.left_power >= 0, c.right_power >= 0), (c.left_power + c.right_power) * .5 * duration),
                (and_(c.left_power <= 0, c.right_power <= 0), 0.0),
                else_=.5 * positive * duration * positive / func.nullif(func.abs(c.right_power - c.left_power), 0))
    # A tagged union returns hours, reasons and provenance from one statement and
    # snapshot; raw samples and JSON payloads never enter the Python process.
    shape = {"tag": String(), "device_id": String(), "hour_epoch": Float(), "active_kw": Float(), "covered_seconds": Float(),
             "available_at": UTCDateTime(), "latest_at": UTCDateTime(), "source_version": String(), "reason": String(),
             "count": BigInteger(), "max_sample_id": BigInteger(), "reverse_count": BigInteger()}
    def fields(**values):
        return [values.get(name, literal(None, type_=kind)).label(name) for name, kind in shape.items()]
    hours = select(*fields(tag=literal("hour"), device_id=c.device_id, hour_epoch=c.hour_end,
                           active_kw=func.sum(area) / 3_600_000, covered_seconds=func.sum(duration),
                           available_at=func.max(c.available_at), count=func.count())).where(c.hour_end <= _hour(now).timestamp()).group_by(c.device_id, c.hour_end)
    valid = select(*fields(tag=literal("valid"), device_id=checked.c.device_id, source_version=checked.c.source_version,
                           latest_at=func.max(checked.c.observed_at), count=func.count(),
                           reverse_count=func.sum(case((checked.c.active_power_w < 0, 1), else_=0)))).where(checked.c.reason.is_(None)).group_by(checked.c.device_id, checked.c.source_version)
    reasons_query = select(*fields(tag=literal("reason"), reason=paired.c.interval_reason, count=func.count())).where(paired.c.interval_reason.is_not(None)).group_by(paired.c.interval_reason)
    totals = select(*fields(tag=literal("total"), count=func.count(), max_sample_id=func.max(checked.c.id))).select_from(checked)
    query = union_all(hours, valid, reasons_query, totals).limit(MAX_AGGREGATE_ROWS + 1)
    rows = db.execute(query).mappings().all()
    metadata = {"aggregated_rows": len(rows), "reader": "sql_window_hour_aggregation", "dialect": dialect, "source_records": None, "max_sample_id": None}
    if len(rows) > MAX_AGGREGATE_ROWS:
        metadata["failure"] = "aggregate_row_budget_exceeded"
        return None, metadata
    hourly, availability, latest, reasons, versions = defaultdict(dict), defaultdict(dict), {}, Counter(), defaultdict(set)
    reverse_records = 0
    for row in rows:
        if row["tag"] == "hour":
            at = datetime.fromtimestamp(row["hour_epoch"], timezone.utc)
            if abs(row["covered_seconds"] - 3600) < .001:
                hourly[row["device_id"]][at] = float(row["active_kw"])
                availability[row["device_id"]][at] = max(at, row["available_at"])
        elif row["tag"] == "valid":
            ident = row["device_id"]
            latest[ident] = max(latest.get(ident, row["latest_at"]), row["latest_at"])
            versions[ident].add(row["source_version"])
            reverse_records += row["reverse_count"]
        elif row["tag"] == "reason":
            reasons[row["reason"]] = row["count"]
        elif row["tag"] == "total":
            metadata.update(source_records=row["count"], max_sample_id=row["max_sample_id"])
    return (hourly, availability, latest, reasons, versions, reverse_records), metadata


def _raw_fields():
    return (Telemetry.id, Telemetry.device_id, Telemetry.observed_at, Telemetry.received_at,
            Telemetry.active_power_w, Telemetry.quality, Telemetry.quality_flags, Telemetry.time_source,
            Telemetry.time_uncertainty_ms, Telemetry.raw_payload, Telemetry.source_mode, Telemetry.source_version,
            Telemetry.boot_epoch, Telemetry.sample_seq, Telemetry.binding_id, Telemetry.campus_id,
            Telemetry.building_id, Telemetry.circuit_id)


def _placement(row):
    return {name: getattr(row, name) for name in ("campus_id", "building_id", "circuit_id", "source_mode")}


def rebuild_hour(db, device_id, hour_end, now):
    return rebuild_forecast_hours(db, device_id, [hour_end], as_of=now)


def rebuild_forecast_hours(db, device_id, hour_ends, as_of=None):
    """Append idempotent closed-hour revisions; caller owns commit and dirty locks.

    Only one device and <=24 hours are loaded. Never locks Device. Adjacency is
    established before placement grouping, so a bad/moved/late point cannot be
    filtered away to bridge an interval. Incomplete revisions are tombstones.
    """
    from .models import ForecastHourRevision
    if db.info.get("campus_ids") is not None:
        raise DomainError("forecast_rebuild_scope", "Projection rebuild requires an unscoped internal session", 403)
    as_of = as_of or utcnow()
    if as_of.tzinfo is None:
        raise DomainError("invalid_forecast_time", "Projection time must include a timezone", 422)
    as_of = as_of.astimezone(timezone.utc)
    hours = sorted(set(hour_ends))
    if not hours or len(hours) > MAX_REBUILD_HOURS or any(h.tzinfo is None or _hour(h) != h for h in hours):
        raise DomainError("invalid_projection_hours", "Use 1–24 timezone-aware whole-hour ends", 422)
    hours = [h.astimezone(timezone.utc) for h in hours]
    if hours[-1] - hours[0] >= MAX_REBUILD_HOURS * HOUR or hours[-1] > as_of:
        raise DomainError("invalid_projection_hours", "Rebuild only closed hours within a 24-hour span", 422)
    device = db.get(Device, device_id)
    if device is None:
        return []
    target = set(hours)
    fields = _raw_fields()
    observation = namedtuple("ForecastRebuildObservation", [field.key for field in fields])
    start, end = hours[0] - HOUR, hours[-1]
    query = select(*fields).where(Telemetry.device_id == device_id, Telemetry.observed_at >= start - timedelta(minutes=30),
                                  Telemetry.observed_at <= min(end + timedelta(minutes=30), as_of), Telemetry.received_at <= as_of
                                  ).order_by(Telemetry.observed_at, Telemetry.id).limit(MAX_REBUILD_SOURCE_ROWS + 1)
    rows = [observation(*row) for row in db.execute(query)]
    if len(rows) > MAX_REBUILD_SOURCE_ROWS:
        raise DomainError("forecast_rebuild_budget_exceeded", "Raw rebuild budget exceeded; use smaller hour batches", 409)
    binding_ids = {row.binding_id for row in rows if row.binding_id is not None}
    bindings = {}
    for offset in range(0, len(binding_ids), 500):
        for binding in db.scalars(select(Binding).where(Binding.id.in_(sorted(binding_ids)[offset:offset + 500]))):
            bindings[binding.id] = binding
    old = list(db.scalars(select(ForecastHourRevision).where(ForecastHourRevision.device_id == device_id,
                          ForecastHourRevision.hour_end.in_(hours), ForecastHourRevision.available_at <= as_of)))
    previous_rows = {(row.hour_end, row.scope_key, row.content_hash): row for row in old}
    latest_rows = {}
    for row in old:
        key = row.hour_end, row.scope_key
        if key not in latest_rows or (row.available_at, row.source_watermark, row.id) > (latest_rows[key].available_at, latest_rows[key].source_watermark, latest_rows[key].id):
            latest_rows[key] = row
    buckets, scope_keys = {}, {}
    def scope_hash(placement):
        identity = tuple(placement[name] for name in ("campus_id", "building_id", "circuit_id", "source_mode"))
        if identity not in scope_keys:
            scope_keys[identity] = payload_hash(placement)
        return scope_keys[identity]
    def bucket(at, placement):
        scope_key = scope_hash(placement)
        key = at, scope_key
        if key not in buckets:
            buckets[key] = {"placement": placement, "hour_end": at, "area": 0.0, "seconds": 0.0, "intervals": 0, "facts": set(),
                            "errors": set(), "versions": set(), "bindings": set(), "boots": set(), "reverse": set(),
                            "known_at": at, "watermark": 0, "latest": None}
        return buckets[key]
    def fact(state, row, reason):
        if row.id in state["facts"]:
            return
        state["facts"].add(row.id)
        state["known_at"] = max(state["known_at"], row.observed_at, row.received_at)
        state["watermark"] = max(state["watermark"], row.id)
        owned = state["hour_end"] - HOUR < row.observed_at <= state["hour_end"]
        if reason and owned:
            state["errors"].add(("sample", row.id, reason))
        elif not reason and _placement(row) == state["placement"]:
            state["versions"].add(row.source_version)
            state["boots"].add(row.boot_epoch)
            if row.binding_id is not None:
                state["bindings"].add(row.binding_id)
            if row.active_power_w < 0 and owned:
                state["reverse"].add(row.id)
            state["latest"] = max(state["latest"] or row.observed_at, row.observed_at)
    prior, prior_reason, prior_placement = None, None, None
    for row in rows:
        placement = _placement(row)
        reason = _record_reason(row, SimpleNamespace(source_mode=row.source_mode, circuit_id=row.circuit_id), bindings.get(row.binding_id))
        own_hour = _hour(row.observed_at) + HOUR
        if own_hour in target:
            fact(bucket(own_hour, placement), row, reason)
        if prior is not None and row.observed_at > prior.observed_at:
            seconds = (row.observed_at - prior.observed_at).total_seconds()
            interval_reason = "invalid_interval_endpoint" if reason or prior_reason else None
            if not interval_reason and row.boot_epoch == prior.boot_epoch and int(row.sample_seq) <= int(prior.sample_seq):
                interval_reason = "sequence_or_time_regression"
            if not interval_reason and seconds > (1800 if row.source_mode == "SIMULATED" else 30):
                interval_reason = "coverage_gap"
            if not interval_reason and (row.boot_epoch != prior.boot_epoch or row.binding_id != prior.binding_id or
                                        row.source_version != prior.source_version or placement != prior_placement):
                interval_reason = "identity_or_source_boundary"
            cursor, stop = max(prior.observed_at, start), min(row.observed_at, end)
            while cursor < stop:
                hour_end = _hour(cursor) + HOUR
                segment_end = min(stop, hour_end)
                if hour_end in target:
                    involved = {_scope: _placement for _scope, _placement in
                                ((scope_hash(placement), placement), (scope_hash(prior_placement), prior_placement))}
                    for part in involved.values():
                        state = bucket(hour_end, part)
                        fact(state, prior, prior_reason)
                        fact(state, row, reason)
                        if interval_reason:
                            state["errors"].add(("interval", (prior.id, row.id), interval_reason))
                    if not interval_reason:
                        state = bucket(hour_end, placement)
                        left = prior.active_power_w + (row.active_power_w - prior.active_power_w) * (cursor - prior.observed_at).total_seconds() / seconds
                        right = prior.active_power_w + (row.active_power_w - prior.active_power_w) * (segment_end - prior.observed_at).total_seconds() / seconds
                        duration = (segment_end - cursor).total_seconds()
                        state["area"] += _positive_area(left, right, duration)
                        state["seconds"] += duration
                        state["intervals"] += 1
                cursor = segment_end
        prior, prior_reason, prior_placement = row, reason, placement
    # A vanished formerly known part must invalidate current evidence explicitly.
    for (at, scope_key), old_row in latest_rows.items():
        if (at, scope_key) not in buckets:
            state = bucket(at, _placement(old_row))
            state["known_at"] = old_row.available_at if not old_row.data.get("source_record_count") else as_of
            state["watermark"] = old_row.source_watermark
            state["errors"].add(("projection", 0, "source_missing_or_removed"))
    values, wanted = [], []
    for (at, scope_key), state in sorted(buckets.items()):
        covered = state["seconds"]
        complete = abs(covered - 3600) < .001
        data = {"import_area_w_seconds": state["area"], "covered_seconds": covered,
                "complete_kw": state["area"] / 3_600_000 if complete else None,
                "interval_count": state["intervals"], "source_record_count": len(state["facts"]),
                "reverse_count": len(state["reverse"]), "exclusion_counts": dict(sorted(Counter(error[-1] for error in state["errors"]).items())),
                "source_versions": sorted(state["versions"]), "binding_ids": sorted(state["bindings"]), "boot_epochs": sorted(state["boots"]),
                "latest_valid_observed_at": iso(state["latest"])}
        previous_revision = latest_rows.get((at, scope_key))
        if previous_revision:
            if previous_revision.data == data and previous_revision.source_watermark == state["watermark"]:
                state["known_at"] = previous_revision.available_at
            elif state["watermark"] <= previous_revision.source_watermark and state["known_at"] <= previous_revision.available_at:
                # Repair/rebuild discovered removed or altered evidence. Do not
                # backdate that correction into earlier backtest origins.
                state["known_at"] = as_of
        identity = {"device_id": device_id, "hour_end": iso(at), "scope_key": scope_key, "available_at": iso(state["known_at"]),
                    "source_watermark": state["watermark"], "data": data}
        digest = payload_hash(identity)
        wanted.append(digest)
        if (at, scope_key, digest) not in previous_rows:
            values.append({"device_id": device_id, **state["placement"], "scope_key": scope_key, "hour_end": at,
                           "available_at": state["known_at"], "computed_at": utcnow(), "source_watermark": state["watermark"],
                           "content_hash": digest, "data": data})
    dialect = db.bind.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise DomainError("unsupported_forecast_projection_dialect", "Projection storage supports SQLite and PostgreSQL", 409)
    if values:
        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        for offset in range(0, len(values), 200):
            db.execute(insert(ForecastHourRevision).values(values[offset:offset + 200]).on_conflict_do_nothing(
                index_elements=["device_id", "scope_key", "hour_end", "content_hash"]))
        db.flush()
    result = []
    for offset in range(0, len(wanted), 500):
        result.extend(db.scalars(select(ForecastHourRevision).where(ForecastHourRevision.device_id == device_id,
                      ForecastHourRevision.hour_end.in_(hours), ForecastHourRevision.content_hash.in_(wanted[offset:offset + 500]))))
    return sorted(result, key=lambda row: (row.hour_end, row.scope_key, row.id))



def forecast_head_evidence(db, devices, now, campus_id=None, building_id=None):
    """Bounded current eligibility shared by the reader and cache identity.

    The normal path bulk-reads registry pointers. An invalid/future pointer gets
    an indexed, at-most-16-sample fallback; stale older good observations must
    invalidate cached cohort eligibility even if bad telemetry keeps arriving.
    """
    selected = {device.id: device for device in devices}
    registry = {device.id: device for device in db.scalars(select(Device).where(Device.id.in_(selected)))}
    pointer_ids = [device.latest_telemetry_id for device in registry.values() if device.latest_telemetry_id is not None]
    pointers = {row.id: row for row in db.scalars(select(Telemetry).where(Telemetry.id.in_(pointer_ids)))} if pointer_ids else {}
    bindings = {}
    def add_bindings(samples):
        ids = sorted({row.binding_id for row in samples if row.binding_id is not None and row.binding_id not in bindings})
        for offset in range(0, len(ids), 500):
            bindings.update({row.id: row for row in db.scalars(select(Binding).where(Binding.id.in_(ids[offset:offset + 500])))})
    add_bindings(pointers.values())
    latest, versions, fallback = {}, defaultdict(set), []
    def accept(device, row):
        if row is None or row.device_id != device.id or row.received_at > now:
            return False
        if campus_id and row.campus_id != campus_id or building_id and row.building_id != building_id:
            return False
        limit = 3600 if device.source_mode == "SIMULATED" else 120
        if not 0 <= (now - row.observed_at).total_seconds() <= limit or _record_reason(row, device, bindings.get(row.binding_id)) is not None:
            return False
        latest[device.id] = max(latest.get(device.id, row.observed_at), row.observed_at)
        versions[device.id].add(row.source_version)
        return True
    for device in devices:
        registered = registry.get(device.id)
        if not accept(device, pointers.get(registered.latest_telemetry_id) if registered else None):
            q = select(Telemetry).where(Telemetry.device_id == device.id, Telemetry.observed_at <= now, Telemetry.received_at <= now,
                    Telemetry.observed_at >= now - timedelta(seconds=3600 if device.source_mode == "SIMULATED" else 120))
            if campus_id:
                q = q.where(Telemetry.campus_id == campus_id)
            if building_id:
                q = q.where(Telemetry.building_id == building_id)
            fallback.extend(db.scalars(q.order_by(Telemetry.observed_at.desc(), Telemetry.id.desc()).limit(MAX_HEAD_SAMPLES)))
    add_bindings(fallback)
    for row in fallback:
        if row.device_id not in latest:
            accept(selected[row.device_id], row)
    return latest, versions

def _read_hourly_projection(db, devices, window_start, now, campus_id=None, building_id=None):
    from .models import ForecastHourRevision
    ids = [device.id for device in devices]
    selected = {device.id: device for device in devices}
    query = select(ForecastHourRevision).where(ForecastHourRevision.device_id.in_(ids),
        ForecastHourRevision.hour_end >= window_start + HOUR, ForecastHourRevision.hour_end <= _hour(now), ForecastHourRevision.available_at <= now)
    if campus_id:
        query = query.where(ForecastHourRevision.campus_id == campus_id)
    if building_id:
        query = query.where(ForecastHourRevision.building_id == building_id)
    if db.info.get("campus_ids") is not None:
        query = query.where(ForecastHourRevision.campus_id.in_(db.info["campus_ids"]))
    rows = list(db.scalars(query.order_by(ForecastHourRevision.hour_end, ForecastHourRevision.available_at, ForecastHourRevision.source_watermark, ForecastHourRevision.id).limit(MAX_AGGREGATE_ROWS + 1)))
    metadata = {"reader": "persistent_hour_revisions", "dialect": db.bind.dialect.name, "aggregated_rows": len(rows),
                "source_records": None, "max_sample_id": max((row.source_watermark for row in rows), default=0)}
    if len(rows) > MAX_AGGREGATE_ROWS:
        return None, metadata | {"failure": "aggregate_row_budget_exceeded"}
    if not rows:
        return None, metadata | {"failure": "projection_pending"}
    by_hour = defaultdict(list)
    for row in rows:
        device = selected[row.device_id]
        if row.source_mode == device.source_mode and row.circuit_id == device.circuit_id:
            by_hour[(row.device_id, row.hour_end)].append(row)
    hourly, availability, versions, reasons = defaultdict(dict), defaultdict(dict), defaultdict(set), Counter()
    reverse_count = 0
    for (ident, at), revisions in by_hour.items():
        changes = defaultdict(list)
        for row in revisions:
            changes[row.available_at].append(row)
        current, history = {}, []
        for known_at, updates in sorted(changes.items()):
            for row in sorted(updates, key=lambda revision: (revision.source_watermark, revision.id)):
                current[row.scope_key] = row
            data = [row.data for row in current.values()]
            valid = all(_finite(part.get("covered_seconds")) and _finite(part.get("import_area_w_seconds")) and
                        0 <= part["covered_seconds"] <= 3600.001 and part["import_area_w_seconds"] >= 0 for part in data)
            covered = sum(part["covered_seconds"] for part in data) if valid else 0
            value = sum(part["import_area_w_seconds"] for part in data) / 3_600_000 if valid and abs(covered - 3600) < .001 else None
            if not history or value != history[-1][1]:
                history.append((known_at, value))
        availability[ident][at] = history
        if history and history[-1][1] is not None:
            hourly[ident][at] = history[-1][1]
        for row in current.values():
            versions[ident].update(row.data.get("source_versions", []))
            reasons.update({"projection_part:" + reason: count for reason, count in row.data.get("exclusion_counts", {}).items()})
            reverse_count += row.data.get("reverse_count", 0)
    latest, head_versions = forecast_head_evidence(db, devices, now, campus_id, building_id)
    for ident, source_versions in head_versions.items():
        versions[ident].update(source_versions)
    return (hourly, availability, latest, reasons, versions, reverse_count), metadata

def forecast_template(devices, campus_id=None, building_id=None, horizon_hours=24, now=None):
    """Pure canonical pending DTO; no source reads, fitting, or persistence."""
    now = now or utcnow()
    if now.tzinfo is None:
        raise DomainError("invalid_forecast_time", "Forecast time must include a timezone", 422)
    now = now.astimezone(timezone.utc)
    origin = _hour(now)
    window_start = origin - timedelta(days=HISTORY_DAYS)
    devices = sorted(devices, key=lambda device: device.id)
    ids, modes = [device.id for device in devices], {device.source_mode for device in devices}
    result = {
        "method": "seasonal_naive", "trained_until": None, "generated_at": iso(now),
        "scope": {"campus_id": campus_id, "building_id": building_id}, "source_mode": _mode(modes),
        "quality": "insufficient_data", "mae_kw": None, "rmse_kw": None,
        "points": [{"timestamp": iso(origin + h * HOUR), "predicted_kw": None, "lower_kw": None, "upper_kw": None} for h in range(1, horizon_hours + 1)],
        "warnings": [],
        "model": {"version": VERSION, "algorithm": "standardized_ridge_regression", "trained": False, "selected_method": "seasonal_naive",
                  "selection_reason": "insufficient_history", "feature_names": FEATURE_NAMES.copy(), "ridge_alpha": RIDGE_ALPHA,
                  "training_sample_count": 0, "minimum_history_hours": MIN_HISTORY_HOURS, "validation": None},
        "holdout": None,
        "coverage": {"selected_device_count": len(ids), "eligible_device_count": 0, "device_ratio": 0.0 if ids else None,
                     "selected_device_ids": ids, "eligible_device_ids": [], "excluded_devices": [], "complete_hours": 0,
                     "expected_hours": 0, "hour_ratio": None, "scope_complete": False, "source_records": None,
                     "excluded_records_and_intervals": {}, "window_start": iso(window_start), "window_end": iso(now)},
        "freshness": {"status": "unknown", "latest_sample_at": None, "oldest_cohort_sample_at": None,
                      "latest_complete_hour": None, "age_seconds": None, "age_basis": "oldest_latest_valid_sample_in_cohort"},
        "provenance": {"source_modes": sorted(modes), "source_versions": [], "training_data": _mode(modes),
                       "measurement": "hourly_mean_import_kw", "aggregation": "current_meter_antichain_fixed_valid_cohort",
                       "reverse_power": "integrate_positive_part_of_linear_signed_power; export_not_forecast",
                       "missing_values": "excluded_intervals_and_incomplete_hours; never_zero_or_extrapolated",
                       "maximum_gap_seconds": {"SIMULATED": 1800, "REPLAYED": 30, "REAL": 30},
                       "hour_coverage_required": 1.0, "as_of_filters": ["observed_at <= issued_at", "received_at <= issued_at"],
                       "query_row_budget": MAX_AGGREGATE_ROWS, "query_row_budget_unit": "aggregated_hour_and_metadata_rows", "cache": "disabled", "external_features": [],
                       "maximum_trailing_forecast_bridge_hours": 1,
                       "dispatch_performed": False, "measured_savings_claim": False, "real_campus_accuracy_claim": False},
    }
    warnings = result["warnings"]
    if "SIMULATED" in modes:
        warnings.append("SIMULATED training/evaluation data; no measured campus accuracy or savings claim")
    if "REPLAYED" in modes:
        warnings.append("REPLAYED observations; retrospective evidence does not establish live campus performance")
    warnings.append("Bounds are empirical holdout 90th-percentile absolute errors, not calibrated confidence intervals or guarantees")
    return result


def forecast(db, campus_id=None, building_id=None, horizon_hours=24, now=None, *, reader="sql"):
    """Return the forecast DTO. Unknown scopes error; insufficient evidence returns nulls."""
    if reader not in {"sql", "projection"}:
        raise DomainError("invalid_forecast_reader", "Choose sql or projection evidence explicitly", 422)
    now = now or utcnow()
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise DomainError("invalid_forecast_time", "Forecast time must include a timezone", 422)
    now = now.astimezone(timezone.utc)
    if isinstance(horizon_hours, bool) or not isinstance(horizon_hours, int) or not 1 <= horizon_hours <= 72:
        raise DomainError("invalid_forecast_horizon", "Use an integer forecast horizon from 1 to 72 hours", 422)
    campus = db.get(Campus, campus_id) if campus_id else None
    building = db.get(Building, building_id) if building_id else None
    if campus_id and campus is None or building_id and building is None:
        raise DomainError("not_found", "Forecast campus or building not found", 404)
    if campus_id and building and building.campus_id != campus_id:
        raise DomainError("scope_mismatch", "Building is not within the requested campus", 422)
    origin, phase = _hour(now), now - _hour(now)
    window_start = origin - timedelta(days=HISTORY_DAYS)
    # Current topology defines the forecast boundary; historical placement is validated below.
    devices = sorted(selected_devices(db, campus_id, building_id, start=now, end=now), key=lambda d: d.id)
    ids, modes = [d.id for d in devices], {d.source_mode for d in devices}
    result = forecast_template(devices, campus_id, building_id, horizon_hours, now)
    warnings = result["warnings"]
    if not ids:
        warnings.append("No eligible metering devices in this scope")
        return result
    if len(ids) > MAX_DEVICES:
        warnings.append("Forecast device budget exceeded; narrow the scope")
        result["model"]["selection_reason"] = "device_budget_exceeded"
        return result
    read_evidence = _read_hourly_projection if reader == "projection" else _read_hourly_sql
    aggregated, reader = read_evidence(db, devices, window_start, now, campus_id, building_id)
    result["coverage"].update({"source_records": reader["source_records"], "aggregated_rows": reader.get("aggregated_rows", 0)})
    result["provenance"].update({"reader": reader.get("reader"), "sql_dialect": reader.get("dialect")})
    if aggregated is None:
        warnings.append("Hourly projections are pending; no synchronous raw fallback was used" if reader["failure"] == "projection_pending" else "Forecast hourly-aggregate budget or SQL dialect is unsupported; no truncated history was trained")
        result["model"]["selection_reason"] = reader["failure"]
        return result
    hourly, available, latest, reasons, versions, reverse_count = aggregated
    result["coverage"]["excluded_records_and_intervals"] = dict(sorted(reasons.items()))
    result["provenance"]["reverse_power_samples"] = reverse_count
    first_hour = min((at for ident, data in available.items() for at in data if at >= window_start + HOUR
                      and any(value is not None for _, value in _evidence_events(hourly[ident], data, at))), default=None)
    if first_hour is None:
        result["coverage"]["excluded_devices"] = [{"device_id": d.id, "reasons": ["no_complete_valid_hours"]} for d in devices]
        warnings.append("No complete calibrated, time-attributed hourly observations")
        return result
    history_hours = int((origin - first_hour) / HOUR) + 1
    result["coverage"]["expected_hours"] = history_hours
    # Disjoint validation and final holdout; each uses up to two daily forecast origins.
    evaluation_hours = 48 if history_hours >= 240 else 24
    validation_start, validation_end = origin - 2 * evaluation_hours * HOUR, origin - evaluation_hours * HOUR
    selection_hours = max(0, int((validation_start - first_hour) / HOUR) + 1)
    eligible = []
    for device in devices:
        problems = []
        training_hours = sum(first_hour <= at <= validation_start and
                             _value_at(hourly[device.id], available[device.id], at, validation_start + phase) is not None
                             for at in available[device.id])
        if selection_hours < 96 or training_hours < max(96, math.ceil(selection_hours * MIN_DEVICE_HOUR_RATIO)):
            problems.append("insufficient_initial_training_coverage")
        stale_after = 3600 if device.source_mode == "SIMULATED" else 120
        if device.id not in latest or (now - latest[device.id]).total_seconds() > stale_after:
            problems.append("stale_or_missing_latest_observation")
        if problems:
            result["coverage"]["excluded_devices"].append({"device_id": device.id, "reasons": problems})
        else:
            eligible.append(device.id)
    result["coverage"].update({"eligible_device_count": len(eligible), "device_ratio": _round(len(eligible) / len(ids)),
                                "eligible_device_ids": eligible, "scope_complete": len(eligible) == len(ids)})
    if len(eligible) < len(ids):
        warnings.append(f"Partial scope: forecasting only {len(eligible)} of {len(ids)} selected meters; excluded loads are unknown, not zero")
    if not eligible or history_hours < MIN_HISTORY_HOURS:
        warnings.append(f"At least {MIN_HISTORY_HOURS} hours of usable history and a fresh fixed cohort are required")
        return result
    series, availability = _combine_histories(eligible, hourly, available, first_hour, origin)
    latest_sample, latest_hour = min(latest[device] for device in eligible), max(series, default=None)
    result["coverage"].update({"complete_hours": len(series), "hour_ratio": _round(len(series) / history_hours)})
    result["freshness"].update({"status": "fresh" if latest_hour and origin - latest_hour <= HOUR else "stale",
                                "latest_sample_at": iso(max(latest[device] for device in eligible)), "oldest_cohort_sample_at": iso(latest_sample),
                                "latest_complete_hour": iso(latest_hour),
                                "age_seconds": (now - latest_sample).total_seconds()})
    eligible_modes = {d.source_mode for d in devices if d.id in eligible}
    result["source_mode"] = _mode(eligible_modes)
    result["provenance"].update({"training_data": _mode(eligible_modes), "source_versions": sorted(set().union(*(versions[d] for d in eligible))),
                                 "cohort_selection": "initial_training_coverage_and_current_freshness; holdout_is_conditional_on_this_fixed_cohort"})
    campus_ids = set(db.scalars(select(Device.campus_id).where(Device.id.in_(eligible))))
    timezones = set(db.scalars(select(Campus.timezone).where(Campus.id.in_(campus_ids))))
    timezone_name = next(iter(timezones)) if len(timezones) == 1 else "UTC"
    try:
        tz = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, TypeError):
        timezone_name, tz = "UTC", timezone.utc
        warnings.append("Unrecognized campus timezone; deterministic UTC calendar features used")
    result["model"]["calendar_timezone"] = timezone_name
    history = _available_history(series, availability, origin, phase)
    fitted = _fit(history, tz)
    result["trained_until"] = iso(max(history, default=None))
    if fitted is None:
        warnings.append("Insufficient uninterrupted lag features to fit ridge regression; forecast unavailable")
        return result
    validation, validation_errors = _backtest(series, availability, validation_start, validation_end, phase, tz)
    holdout, holdout_errors = _backtest(series, availability, validation_end, origin, phase, tz)
    enough_validation = validation["sample_count"] >= MIN_SCORE_SAMPLES
    if enough_validation and mean(abs(x) for x in validation_errors["ridge_regression"]) < .99 * mean(abs(x) for x in validation_errors["seasonal_naive"]):
        method, selection_reason = "ridge_regression", "validation_mae_improved_by_more_than_1_percent"
    else:
        method = "seasonal_naive"
        selection_reason = "baseline_equal_or_better_on_validation" if enough_validation else "insufficient_paired_validation_evidence"
    model_identity = sha256(json.dumps({"version": VERSION, "cohort": eligible, "last_row_id": reader["max_sample_id"],
                                      "rows": reader["source_records"], "as_of": iso(now), "coefficients": fitted["coefficients"]}, sort_keys=True).encode()).hexdigest()[:20]
    result["model"].update({"trained": True, "selected_method": method, "selection_reason": selection_reason,
                            "training_sample_count": fitted["sample_count"], "training_start": iso(fitted["start"]), "validation": validation,
                            "prediction_origin": iso(max(history)), "bridge_hours": int((origin - max(history)) / HOUR),
                            "id": model_identity, "standardized_coefficients": {name: _round(c) for name, c in zip(FEATURE_NAMES, fitted["coefficients"])},
                            "feature_centers": [_round(v) for v in fitted["centers"]], "feature_scales": fitted["scales"].copy(),
                            "intercept_kw": _round(fitted["intercept"]), "prediction_upper_cap_kw": _round(fitted["upper"]),
                            "outlier_policy": "fit-only 3x training-target p95 cap; held-out actuals remain unclipped"})
    errors = holdout_errors[method]
    radius = _quantile([abs(x) for x in errors], .90) if len(errors) >= MIN_SCORE_SAMPLES else None
    selected_metrics, baseline_metrics = holdout["models"][method], holdout["models"]["seasonal_naive"]
    baseline_mae = baseline_metrics["mae_kw"]
    holdout.update({"selected_method": method,
                    "baseline_improvement_pct": _round(100 * (baseline_mae - selected_metrics["mae_kw"]) / baseline_mae) if baseline_mae else None,
                    "band": {"method": "empirical_absolute_holdout_residual", "quantile": .90, "radius_kw": _round(radius), "guaranteed": False},
                    "selection_used_holdout": False, "protocol": "expanding_daily_issue_times_recursive_24h; at_most_1h_trailing_forecast_bridge; paired_complete_targets_only"})
    result.update({"method": method, "holdout": holdout, "mae_kw": selected_metrics["mae_kw"], "rmse_kw": selected_metrics["rmse_kw"]})
    if holdout["sample_count"] < MIN_SCORE_SAMPLES or not enough_validation:
        warnings.append("Insufficient paired validation/holdout targets; forecasts withheld rather than presenting unvalidated estimates")
        return result
    if result["model"]["bridge_hours"]:
        warnings.append(f'Forecast origin is {iso(max(history))}; {result["model"]["bridge_hours"]} unavailable recent hour(s) are modeled, never treated as observations')
    predictions = _predict(history, origin, horizon_hours, method, fitted, tz)
    for point, (at, value) in zip(result["points"], predictions.items()):
        point.update({"predicted_kw": _round(value), "lower_kw": _round(max(0.0, value - radius)) if value is not None and radius is not None else None,
                      "upper_kw": _round(value + radius) if value is not None and radius is not None else None})
    complete_forecast = all(p["predicted_kw"] is not None for p in result["points"])
    result["quality"] = ("model_estimate" if method == "ridge_regression" else "baseline_estimate") if complete_forecast else "insufficient_data"
    if complete_forecast and (not result["coverage"]["scope_complete"] or result["coverage"]["hour_ratio"] < .95 or result["model"]["bridge_hours"]):
        result["quality"] = "partial_estimate"
    if not complete_forecast:
        warnings.append("Required seasonal or recursive lag observations are missing; affected points remain unknown")
    if horizon_hours > 24:
        warnings.append("Beyond 24 hours, predictions recurse; displayed error bands were evaluated only on 1–24-hour horizons")
    if reverse_count:
        warnings.append("Reverse power observed: forecast covers positive import only, not net power or export")
    if method == "seasonal_naive":
        warnings.append("Seasonal-naive baseline selected by validation; training a model does not imply it performs better")
    return result
