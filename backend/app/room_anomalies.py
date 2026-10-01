"""Interpretable room anomalies: conditional historical baseline + bounded rules.
No weather, AI, causal savings or physical safety is inferred from these samples.
"""
from datetime import timedelta
from statistics import median
from zoneinfo import ZoneInfo
from sqlalchemy import select, or_
from .models import Space, RoomAnomaly, Campus, ChannelObservation, DeviceChannel, Binding, RoomMode, Device
from .classrooms import snapshots, timeline, _load, _at, audit_room, EvidenceSet
from .common import uid, record_dict
from .db import utcnow, iso

RULE_VERSION = "classroom-conditional-baseline-v1"


def conditional_baseline(db, space, at, occupancy, source_mode=None, config=None):
    from .room_rules import rule_for
    config = config or rule_for(db,space)["config"]
    cutoff = at-timedelta(days=1)
    start = at-timedelta(days=28)
    loaded = _load(db, [space], start, cutoff)
    loaded = EvidenceSet((*loaded[:3], [r for r in loaded[3] if r.received_at <= at], loaded[4]), space.id)
    source_mode = source_mode or snapshots(db, [space], at)[0]["source_mode"]
    campus = db.get(Campus, space.campus_id)
    zone = ZoneInfo(campus.timezone if campus else "UTC")
    target_local = at.astimezone(zone)
    target_weekend = target_local.weekday() >= 5
    # Distinct quarter-hour buckets avoid inflating evidence with high-rate bursts.
    buckets = {}
    for row in loaded[3]:
        if row.quality == "good" and row.value.get("active_power_w") is not None and start <= row.observed_at < cutoff:
            key = int(row.observed_at.timestamp()) // 900
            buckets[key] = max(buckets.get(key, row.observed_at), row.observed_at)
    times = sorted(buckets.values())
    values, dates = [], set()
    for moment in times:
        local = moment.astimezone(zone)
        hour_distance = min((local.hour-target_local.hour)%24, (target_local.hour-local.hour)%24)
        if (local.weekday() >= 5) != target_weekend or hour_distance > 1:
            continue
        state = _at(space, moment, loaded)
        if state["occupancy"] == occupancy and occupancy != "unknown" and state["observed_power_w"] is not None and state["quality"] == "good" and state["source_mode"] == source_mode and source_mode not in {"MIXED", "UNKNOWN"}:
            values.append(state["observed_power_w"])
            dates.add(local.date())
    enough = len(values) >= 8 and len(dates) >= 3
    center = median(values) if enough else None
    mad = median(abs(v-center) for v in values) if enough else None
    threshold = max(config["high_load_minimum_w"], center*config["baseline_multiplier"], center+config["baseline_mad_multiplier"]*1.4826*mad) if enough else None
    return {"baseline_median_w": center, "baseline_mad_w": mad, "baseline_sample_count": len(values),
        "baseline_status": "sufficient" if enough else "insufficient", "threshold_w": threshold,
        "baseline_condition": f"Same room and {source_mode} source, {occupancy} observations, local hour ±1, same weekday/weekend class, historical data strictly 1–28 days before target; minimum 8 quarter-hour samples across 3 dates; no weather model"}


def persistence(intervals, predicate):
    total, beginning = 0., None
    for segment in reversed(intervals):
        if not predicate(segment):
            break
        total += segment["duration_seconds"]
        beginning = segment["start"]
    return total, beginning


def evaluate_room(db, space, now=None):
    now = now or utcnow()
    db.scalar(select(Space.id).where(Space.id == space.id).with_for_update())
    from .room_rules import rule_for
    rule=rule_for(db,space)
    config=rule["config"]
    if not config["enabled"]:
        return []
    state = snapshots(db, [space], now)[0]
    history = timeline(db, space, now-timedelta(seconds=max(3600,config["vacant_persistence_seconds"],config["data_quality_persistence_seconds"],config["high_load_persistence_seconds"])), now)
    baseline = conditional_baseline(db, space, now, state["occupancy"], state["source_mode"],config)
    rules = {
        "vacant_load": (config["vacant_persistence_seconds"], lambda s: s["occupancy"] == "vacant" and s["observed_power_w"] is not None and s["observed_power_w"] > config["vacant_power_threshold_w"],
            "Vacancy and demand above the configured threshold persisted; inspect noncritical loads. Presence is not proof of electrical safety.", "warning"),
        "protective_mode": (0, lambda s: s["mode"] == "fault",
            "Room protective/fault mode is active; inspect local interlocks. This does not establish a physical failure or safe voltage absence.", "critical"),
        "data_quality": (config["data_quality_persistence_seconds"], lambda s: s["occupancy"] == "unknown" or s["observed_power_w"] is None,
            "Fresh presence/power coverage is incomplete. Unknown must not trigger vacancy-based shedding.", "warning"),
    }
    if baseline["threshold_w"] is not None:
        rules["conditional_high_load"] = (config["high_load_persistence_seconds"], lambda s: s["occupancy"] == state["occupancy"] and s["observed_power_w"] is not None and s["observed_power_w"] > baseline["threshold_w"],
            "Observed demand exceeds the conditional historical robust baseline for the persistence window; correlation, not diagnosis.", "warning")
    active = {r.type: r for r in db.scalars(select(RoomAnomaly).where(RoomAnomaly.space_id == space.id, RoomAnomaly.status != "resolved"))}
    if "conditional_high_load" in active and "conditional_high_load" not in rules:
        prior = active["conditional_high_load"]
        prior.evidence = {**prior.evidence, **baseline, "evaluated_at": iso(now), "explanation": "The previous episode cannot currently be re-evaluated: conditional baseline or fresh evidence is insufficient; no automatic clear is inferred."}
    results = []
    for kind, (required, predicate, explanation, severity) in rules.items():
        seconds, beginning = persistence(history["intervals"], predicate)
        qualifies = predicate(state) and seconds >= required
        existing = active.get(kind)
        resolved = db.scalar(select(RoomAnomaly).where(RoomAnomaly.space_id == space.id, RoomAnomaly.type == kind,
            RoomAnomaly.status == "resolved").order_by(RoomAnomaly.resolved_at.desc()).limit(1))
        known_clear = state["occupancy"] != "unknown" and state["observed_power_w"] is not None and not predicate(state)
        if kind == "vacant_load" and state["occupancy"] == "vacant" and state["observed_power_w"] is not None:
            known_clear = state["observed_power_w"] <= config["vacant_power_threshold_w"]*(1-config["clear_hysteresis_ratio"])
        if kind == "conditional_high_load" and state["observed_power_w"] is not None:
            known_clear = state["observed_power_w"] <= baseline["threshold_w"]*(1-config["clear_hysteresis_ratio"])
        if kind in {"data_quality", "protective_mode"}:
            known_clear = not predicate(state)
        if resolved and known_clear and not any(n["action"] == "condition_cleared" for n in resolved.notes):
            resolved.notes = [*resolved.notes, {"at": iso(now), "by": "anomaly-service", "action": "condition_cleared", "text": "Fresh evidence broke the previously resolved episode"}]
        if qualifies:
            beginning = beginning or now
            # A manual resolution suppresses the same continuing episode; a new
            # observed break is required to open another episode.
            if not existing and resolved and resolved.evidence.get("rule_revision",0)==rule["revision"] and not any(n["action"] == "condition_cleared" for n in resolved.notes):
                resolved.last_observed_at = now
                continue
            if rule["updated_at"]:
                beginning=max(beginning,rule["updated_at"])
            evidence = {"rule_revision":rule["revision"],"clear_threshold_w":None,"rule_version": RULE_VERSION, "evaluated_at": iso(now), "persistence_seconds": seconds,
                "required_persistence_seconds": required, "observed_power_w": state["observed_power_w"], **baseline,
                "observation_ids": [c["observation_id"] for c in state["channels"] if c["observation_id"] is not None],
                "quality_flags": sorted({f for c in state["channels"] for f in c["quality_flags"]}), "explanation": explanation}
            if kind == "vacant_load":
                evidence["threshold_w"] = config["vacant_power_threshold_w"]
            elif kind in {"data_quality", "protective_mode"}:
                evidence.update(threshold_w=None, baseline_status="not_applicable")
            if evidence["threshold_w"] is not None:
                evidence["clear_threshold_w"] = evidence["threshold_w"]*(1-config["clear_hysteresis_ratio"])
            if existing:
                existing.last_observed_at, existing.evidence = now, evidence
            else:
                existing = RoomAnomaly(id=uid("room_alarm"), space_id=space.id, campus_id=space.campus_id,
                    building_id=space.building_id, type=kind, severity=severity, status="open", episode_start=beginning,
                    last_observed_at=now, source_mode=state["source_mode"], evidence=evidence,
                    notes=[{"at": iso(now), "by": "anomaly-service", "action": "opened", "text": explanation}])
                db.add(existing)
                audit_room(db, "anomaly-service", "opened", space, "room_anomaly", existing.id, {"type": kind})
            results.append(existing)
        elif existing:
            # Missing observations cannot prove a previous high-load episode ended.
            if known_clear:
                existing.status, existing.resolved_at = "resolved", now
                existing.notes = [*existing.notes, {"at": iso(now), "by": "anomaly-service", "action": "condition_cleared", "text": "Fresh observations no longer meet the rule condition; automatically resolved"}]
                audit_room(db, "anomaly-service", "resolved", space, "room_anomaly", existing.id, {"fresh_clear": True})
                results.append(existing)
    db.flush()
    return results


def evaluate_batch(factory, batch_size=8, now=None):
    """Bounded independent analysis work, never a full-campus transaction in control."""
    from .models import State, Space
    from .worker import lock
    now = now or utcnow()
    with factory() as db:
        if not lock(db, 48392719):
            return 0
        state = db.get(State, "classroom_anomaly_worker")
        values = state.value if state else {}
        if now.timestamp()-values.get("last_tick_epoch", 0) < 1:
            return 0
        query = select(Space).order_by(Space.id).limit(batch_size)
        cursor = values.get("cursor")
        rows = list(db.scalars(query.where(Space.id > cursor) if cursor else query))
        if not rows and cursor:
            rows = list(db.scalars(query))
        for room in rows:
            evaluate_room(db, room, now)
        values = {"cursor": rows[-1].id if rows else None, "last_tick_at": iso(now), "last_tick_epoch": now.timestamp(),
            "rooms_checked": len(rows), "physical_actions": False, "rule_version": RULE_VERSION}
        if state:
            state.value = values
        else:
            db.add(State(key="classroom_anomaly_worker", value=values))
        db.commit()
        return len(rows)
