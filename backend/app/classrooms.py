"""Room state reconstructed from immutable event-time evidence, never latest pointers.

Intervals are [start, end). Every observation is cut by freshness, the next
observation, and its historical binding. Missing/invalid evidence stays unknown.
"""
from collections import defaultdict
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, or_, and_
from sqlalchemy.exc import IntegrityError
from .common import DomainError, require_entity, uid, record_dict, payload_hash
from .db import utcnow, iso
from .models import (Space, Device, Binding, DeviceChannel, ChannelObservation,
    RoomMode, RoomAnomaly, ScheduleEvent, ChannelHold, Building, Floor, Campus, Audit, Event)

MAX_WINDOW_SECONDS = 7 * 86400


def aware(at):
    if at.tzinfo is None:
        raise DomainError("timezone_required", "Timestamp must include a UTC offset", 422)
    return at.astimezone(timezone.utc)


def window(start, end):
    start, end = aware(start), aware(end)
    if not 0 < (end-start).total_seconds() <= MAX_WINDOW_SECONDS:
        raise DomainError("invalid_window", "Window must be positive and at most seven days", 422)
    return start, end


def audit_room(db, actor, action, space, entity_type="room", entity_id=None, details=None):
    entity_id = entity_id or space.id
    db.add(Audit(actor=actor, action=action, entity_type=entity_type, entity_id=entity_id,
        campus_id=space.campus_id, details=details or {}))
    db.add(Event(campus_id=space.campus_id, type=f"{entity_type}.{action}", entity_id=entity_id))


def register_channel(db, body, actor):
    device = require_entity(db, Device, body.device_id)
    if db.get(DeviceChannel, body.id):
        raise DomainError("already_exists", "Channel identity already exists", 409)
    if body.controllable:
        required = {"relay.commanded"} if device.kind in {"switch", "light"} else {"relay.feedback", "relay.commanded"}
        if body.kind not in {"lighting", "socket"} or not required.issubset(body.capabilities):
            raise DomainError("unsupported_capability", "Controllable channel needs relay command and feedback capabilities", 422)
        if device.kind not in {"switch", "light"} and db.scalar(select(DeviceChannel).where(DeviceChannel.device_id == device.id, DeviceChannel.controllable.is_(True))):
            raise DomainError("ambiguous_actuator", "Only one independently addressable actuator may use a device-level command target", 409)
        if device.source_mode != "SIMULATED":
            raise DomainError("physical_control_disabled", "New classroom actuation is simulation-only", 409)
    row = DeviceChannel(**body.model_dump(), campus_id=device.campus_id)
    db.add(row)
    db.flush()
    return row


def ingest_channel(db, sample, received_at=None, event_id=None, telemetry_id=None, relative_proof=None):
    db.flush()
    received_at = received_at or utcnow()
    channel = require_entity(db, DeviceChannel, sample.channel_id)
    device = require_entity(db, Device, channel.device_id)
    if sample.source_mode != device.source_mode:
        raise DomainError("source_mode_mismatch", "Channel source must match its device", 409)
    identity = (ChannelObservation.channel_id == channel.id, ChannelObservation.boot_epoch == sample.boot_epoch,
        ChannelObservation.sample_seq == sample.sample_seq)
    digest = payload_hash(sample.model_dump(mode="json"))
    prior = db.scalar(select(ChannelObservation).where(*identity))
    if prior:
        if prior.payload_hash != digest:
            raise DomainError("channel_sample_conflict", "Sample identity has different content", 409)
        return prior, False
    values = sample.value.model_dump(exclude_none=True)
    allowed = {"presence": {"occupancy"}, "lighting": {"output_present", "actuator_reported_on", "desired_on", "active_power_w", "fault_latched"},
        "socket": {"output_present", "actuator_reported_on", "desired_on", "active_power_w", "fault_latched"}, "power": {"active_power_w"},
        "temperature": {"number"}, "illuminance": {"number"}, "co2": {"number"}}[channel.kind]
    for field, capability in (("output_present","relay.feedback"),("actuator_reported_on","relay.commanded"),("active_power_w","power.active")):
        if field in values and capability not in channel.capabilities:
            raise DomainError("unsupported_channel_measurement", f"{field} requires declared {capability} capability", 422)
    if set(values)-allowed:
        raise DomainError("channel_value_mismatch", "Values do not match the declared channel capability", 422)
    if values.get("occupancy") == "vacant" and not any(x in channel.capabilities for x in ("presence.radar", "presence.occupancy")):
        raise DomainError("vacancy_not_supported", "PIR silence cannot establish vacancy", 422)
    at = relative_proof["knowledge_at"] if relative_proof else sample.observed_at or received_at
    time_basis = "authenticated_relative_receipt" if relative_proof else "device_observed" if sample.observed_at else "received_only"
    measured_at = sample.observed_at
    measurement_age_ms = relative_proof["measurement_age_ms"] if relative_proof else None
    flags = []
    if not sample.valid:
        flags.append("MEASUREMENT_INVALID")
    if not relative_proof and (sample.time_source in {"received_only", "device_clock"} or sample.time_uncertainty_ms is None or sample.time_uncertainty_ms > 5000):
        flags.append("TIME_UNCERTAIN")
    if at > received_at + timedelta(seconds=5):
        flags.append("FUTURE_TIMESTAMP")
    previous = db.scalar(select(ChannelObservation).where(ChannelObservation.channel_id == channel.id,
        ChannelObservation.boot_epoch == sample.boot_epoch).order_by(ChannelObservation.observed_at.desc(), ChannelObservation.id.desc()).limit(1))
    if previous and (int(sample.sample_seq)-int(previous.sample_seq)) * (at-previous.observed_at).total_seconds() < 0:
        flags.append("SEQUENCE_TIME_CONFLICT")
    binding = db.scalar(select(Binding).where(Binding.device_id == device.id, Binding.valid_from <= at,
        or_(Binding.valid_to.is_(None), Binding.valid_to > at)).order_by(Binding.valid_from.desc()).limit(1))
    if not binding:
        flags.append("BINDING_UNKNOWN")
    owner = binding or device
    channel.introduced_at = min(channel.introduced_at or channel.created_at, at)
    if relative_proof and binding and at-timedelta(milliseconds=measurement_age_ms) < binding.valid_from:
        flags.append("BINDING_TIME_AMBIGUOUS")
    freshness_ms = min(channel.freshness_seconds*1000, relative_proof["maximum_age_ms"]) if relative_proof else channel.freshness_seconds*1000
    valid_until = at + timedelta(milliseconds=freshness_ms-(measurement_age_ms or 0))
    if binding and binding.valid_to:
        valid_until = min(valid_until, binding.valid_to)
    row = ChannelObservation(channel_id=channel.id, device_id=device.id, event_id=event_id, telemetry_id=telemetry_id,
        boot_epoch=sample.boot_epoch, sample_seq=sample.sample_seq, observed_at=at, measured_at=measured_at, time_basis=time_basis, measurement_age_ms=measurement_age_ms, received_at=received_at, valid_until=valid_until,
        value=values, quality="invalid" if not sample.valid else "uncertain" if flags else "good", quality_flags=flags,
        source_mode=sample.source_mode, source_version=sample.source_version, payload_hash=digest,
        campus_id=owner.campus_id, building_id=owner.building_id, space_id=owner.space_id, binding_id=binding.id if binding else None)
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        existing = db.scalar(select(ChannelObservation).where(*identity))
        if not existing or existing.payload_hash != digest:
            raise DomainError("channel_sample_conflict", "Concurrent sample identity conflict", 409)
        return existing, False
    device.last_seen_at = max(device.last_seen_at or received_at, received_at)
    return row, True


def mirror_telemetry(db, telemetry):
    """A projection of the same sample identity, never an extra energy ledger."""
    from .classroom_schemas import ChannelSample, ChannelValue
    device = db.get(Device, telemetry.device_id)
    if device and device.kind in {"switch", "light"}:
        return  # Canonical Switch channels preserve their own capability-specific quality.
    channels = db.scalars(select(DeviceChannel).where(DeviceChannel.device_id == telemetry.device_id,
        DeviceChannel.kind.in_(["socket", "lighting", "power"]))).all()
    for channel in channels:
        value = {"active_power_w": telemetry.active_power_w} if "power.active" in channel.capabilities else {}
        if channel.kind != "power":
            value.update(output_present=telemetry.output_present, desired_on=telemetry.desired_on, fault_latched=telemetry.fault_latched)
        sample = ChannelSample(channel_id=channel.id, boot_epoch=telemetry.boot_epoch, sample_seq=telemetry.sample_seq,
            observed_at=telemetry.observed_at, time_source="simulated" if telemetry.source_mode == "SIMULATED" else "authenticated" if telemetry.time_source == "authenticated" else "received_only",
            time_uncertainty_ms=telemetry.time_uncertainty_ms, source_mode=telemetry.source_mode, source_version=telemetry.source_version,
            valid=telemetry.quality == "good", value=ChannelValue(**value))
        ingest_channel(db, sample, received_at=telemetry.received_at, telemetry_id=telemetry.id)


def room_query(campus_id=None, building_id=None, floor_id=None, space_id=None):
    query = select(Space)
    for field, value in (("campus_id", campus_id), ("building_id", building_id), ("floor_id", floor_id), ("id", space_id)):
        if value:
            query = query.where(getattr(Space, field) == value)
    return query.order_by(Space.campus_id, Space.building_id, Space.floor_id, Space.name, Space.id)


def mode_at(rows, at):
    active = [r for r in rows if r.starts_at <= at and (r.ends_at is None or at < r.ends_at)]
    # Safety modes prevail even if a later override was accidentally overlapping.
    priority = {"manual": 0, "automatic": 0, "maintenance": 1, "fault": 2}
    row = max(active, key=lambda r: (priority[r.mode], r.starts_at, r.created_at, r.id)) if active else None
    return (row.mode, row.ends_at, row.reason) if row else ("manual", None, "No active automatic authorization")


def effective_mode(db, space_id, at=None):
    at = at or utcnow()
    rows = db.scalars(select(RoomMode).where(RoomMode.space_id == space_id, RoomMode.starts_at <= at,
        or_(RoomMode.ends_at.is_(None), RoomMode.ends_at > at))).all()
    return mode_at(rows, at)


def set_mode(db, space, body, actor, now=None):
    now = now or utcnow()
    # Serializing against the room prevents concurrent holds creating overlap.
    db.scalar(select(Space).where(Space.id == space.id).with_for_update())
    for old in db.scalars(select(RoomMode).where(RoomMode.space_id == space.id, RoomMode.starts_at <= now,
        or_(RoomMode.ends_at.is_(None), RoomMode.ends_at > now))):
        if body.mode != "manual" or old.mode == "manual":
            old.ends_at = now
    row = RoomMode(id=uid("mode"), space_id=space.id, campus_id=space.campus_id, mode=body.mode, starts_at=now,
        ends_at=now+timedelta(seconds=body.duration_seconds) if body.duration_seconds else None, reason=body.reason, created_by=actor)
    db.add(row)
    audit_room(db, actor, "mode_changed", space, details=body.model_dump())
    db.flush()
    return row


def source_summary(modes):
    values = set(modes)-{"UNKNOWN"}
    return next(iter(values)) if len(values) == 1 else "MIXED" if values else "UNKNOWN"


class EvidenceSet(tuple):
    def __new__(cls, values, space_id=None):
        obj = super().__new__(cls, values)
        obj.space_id = space_id
        obj.by_channel = defaultdict(list)
        for row in values[3]:
            obj.by_channel[row.channel_id].append(row)
        return obj


def partition_evidence(loaded, spaces):
    bindings, channels, devices, observations, modes = loaded
    brooms, orooms, mrooms, cdevices = (defaultdict(list) for _ in range(4))
    for row in bindings:
        brooms[row.space_id].append(row)
    for row in observations:
        orooms[row.space_id].append(row)
    for row in modes:
        mrooms[row.space_id].append(row)
    for row in channels:
        cdevices[row.device_id].append(row)
    return {space.id: EvidenceSet((brooms[space.id], [c for d in {b.device_id for b in brooms[space.id]} for c in cdevices[d]],
        devices, orooms[space.id], mrooms[space.id]), space.id) for space in spaces}


def _load(db, spaces, start, end, latest_only=False):
    room_ids = [r.id for r in spaces]
    bindings = list(db.scalars(select(Binding).where(Binding.space_id.in_(room_ids), Binding.valid_from <= end,
        or_(Binding.valid_to.is_(None), Binding.valid_to > start))).all())
    device_ids = list({b.device_id for b in bindings})
    channels = list(db.scalars(select(DeviceChannel).where(DeviceChannel.device_id.in_(device_ids), func.coalesce(DeviceChannel.introduced_at, DeviceChannel.created_at) <= end).execution_options(authorized_historical_identity=True)).all())
    devices = {d.id: d for d in db.scalars(select(Device).where(Device.id.in_(device_ids)).execution_options(authorized_historical_identity=True))}
    # Observations retain historical scope. The current registry is never used to
    # choose observation ownership; channel metadata is joined only after this.
    query = select(ChannelObservation).where(ChannelObservation.space_id.in_(room_ids),
        ChannelObservation.observed_at <= end, ChannelObservation.observed_at >= start-timedelta(seconds=3600))
    if latest_only:
        rank = select(ChannelObservation.id, func.row_number().over(partition_by=ChannelObservation.channel_id,
            order_by=(ChannelObservation.observed_at.desc(), ChannelObservation.id.desc())).label("rn")).where(
                ChannelObservation.space_id.in_(room_ids), ChannelObservation.observed_at <= end).subquery()
        query = select(ChannelObservation).join(rank, rank.c.id == ChannelObservation.id).where(rank.c.rn == 1)
    observations = list(db.scalars(query.order_by(ChannelObservation.observed_at, ChannelObservation.id)))
    modes = list(db.scalars(select(RoomMode).where(RoomMode.space_id.in_(room_ids), RoomMode.starts_at <= end,
        or_(RoomMode.ends_at.is_(None), RoomMode.ends_at > start))))
    return EvidenceSet((bindings, channels, devices, observations, modes), spaces[0].id if len(spaces) == 1 else None)


def _channel_state(channel, device, binding, sample, at, mode, current=False):
    quality, flags, value = "unknown", ["NO_OBSERVATION"], None
    if sample:
        flags = list(sample.quality_flags)
        if sample.binding_id != binding.id:
            quality, flags = "unknown", [*flags, "BINDING_MISMATCH"]
        elif sample.observed_at > at:
            quality, flags = "unknown", ["FUTURE_OBSERVATION"]
        elif at >= sample.valid_until or (binding.valid_to and at >= binding.valid_to):
            quality, flags = "stale", [*flags, "STALE_OBSERVATION"]
        else:
            quality = sample.quality
            if quality == "good":
                value = sample.value
    age = (at-sample.observed_at).total_seconds() if sample else None
    online = "unknown" if age is None else "online" if quality == "good" else "offline" if age > max(600, channel.freshness_seconds*3) else "stale"
    block = None
    if not channel.controllable:
        block = "read_only_channel"
    elif not current:
        block = "historical_view"
    elif device.source_mode != "SIMULATED":
        block = "physical_control_disabled"
    elif mode in {"maintenance", "fault"}:
        block = f"room_{mode}_interlock"
    elif device.critical or not device.allow_control or not device.commissioned:
        block = "device_not_control_authorized"
    elif quality != "good" or not value or (value.get("actuator_reported_on") if device.kind in {"switch", "light"} else value.get("output_present")) is None or value.get("fault_latched") is not False:
        block = "stale_or_unknown_feedback"
    family = "SWITCH" if device.kind in {"switch", "light"} else "PLUG" if device.kind == "smart_plug" else "PRESENCE" if device.kind == "presence" else "METER" if device.kind == "meter" else "SENSOR"
    return {"channel_id": channel.id, "channel_key": channel.channel_key, "device_id": device.id, "name": channel.name,
        "kind": channel.kind, "product_family": family, "capabilities": channel.capabilities, "unit": channel.unit,
        "value": value, "quality": quality, "quality_flags": flags, "observed_at": (sample.measured_at if sample.time_basis != "device_observed" else sample.observed_at) if sample else None,
        "effective_at": sample.observed_at if sample else None, "time_basis": sample.time_basis if sample else "unknown", "measurement_age_ms": sample.measurement_age_ms if sample else None,
        "received_at": sample.received_at if sample else None, "valid_until": min(sample.valid_until, binding.valid_to) if sample and binding.valid_to else sample.valid_until if sample else None,
        "observation_id": sample.id if sample else None, "binding_id": binding.id, "source_mode": sample.source_mode if sample else device.source_mode,
        "source_version": sample.source_version if sample else None, "online_status": online, "controllable": channel.controllable,
        "feedback_supported": "relay.feedback" in channel.capabilities,
        "verification_kind": "actuator_reported_only" if device.kind in {"switch", "light"} and channel.kind == "lighting" else "independent_feedback" if channel.kind in {"socket", "lighting"} and "relay.feedback" in channel.capabilities else "not_applicable",
        "manual_hold_until": None, "manual_hold_scope": None,
        "allowed_actions": [a for a in ("hold", "shed", "restore") if a in device.capabilities] if not block else [], "block_reason": block}


def _aggregate(channels):
    presence = [c for c in channels if c["kind"] == "presence"]
    states = [c["value"].get("occupancy", "unknown") if c["value"] else "unknown" for c in presence]
    required_presence = [c for c in presence if any(cap in c["capabilities"] for cap in ("presence.radar", "presence.occupancy"))]
    vacant_states = [c["value"].get("occupancy", "unknown") if c["value"] else "unknown" for c in required_presence]
    occupancy = "occupied" if "occupied" in states else "vacant" if vacant_states and all(s == "vacant" for s in vacant_states) else "unknown"
    def load(kind):
        channels_of_kind = [c for c in channels if c["kind"] == kind]
        values = [(c["value"].get("actuator_reported_on") if c["verification_kind"] == "actuator_reported_only" else c["value"].get("output_present")) if c["value"] else None for c in channels_of_kind]
        if not values or any(v is None for v in values):
            return "unknown"
        return "on" if all(values) else "off" if not any(values) else "mixed"
    # One aggregate measurement per device: Switch has one three-gang meter,
    # never three fabricated per-relay meters; Plug has one measured output.
    powered_by_device = {}
    for channel in channels:
        if "power.active" in channel["capabilities"] and channel["kind"] in {"lighting", "socket", "power"}:
            if channel["device_id"] not in powered_by_device or channel["kind"] == "power":
                powered_by_device[channel["device_id"]] = channel
    powered = list(powered_by_device.values())
    powers = [c["value"].get("active_power_w") if c["value"] else None for c in powered]
    known = [v for v in powers if v is not None]
    # Partial totals must not masquerade as complete room demand.
    power = sum(known) if powers and len(known) == len(powers) else None
    lighting_kinds = {c["verification_kind"] for c in channels if c["kind"] == "lighting" and c["quality"] == "good" and c["verification_kind"] != "not_applicable"}
    lighting_verification = next(iter(lighting_kinds)) if len(lighting_kinds) == 1 else "mixed" if lighting_kinds else "unknown"
    return {"lighting_verification_kind": lighting_verification, "occupancy": occupancy, "lighting": load("lighting"), "sockets": load("socket"),
        "observed_power_w": power, "power_coverage": len(known)/len(powers) if powers else 0.,
        "source_mode": source_summary(c["source_mode"] for c in channels),
        "quality": "good" if channels and all(c["quality"] == "good" for c in channels) else "partial" if any(c["quality"] == "good" for c in channels) else "unknown"}


def _at(space, at, loaded, current=False):
    bindings, channels, devices, observations, modes = loaded
    active = {b.device_id: b for b in bindings if b.space_id == space.id and b.valid_from <= at and (b.valid_to is None or at < b.valid_to)}
    latest = {}
    for channel_id, rows in loaded.by_channel.items():
        position = bisect_right(rows, at, key=lambda row: row.observed_at)
        if position and rows[position-1].space_id == space.id:
            latest[channel_id] = rows[position-1]
    mode, expiry, reason = mode_at([r for r in modes if r.space_id == space.id], at)
    states = [_channel_state(c, devices[c.device_id], active[c.device_id], latest.get(c.id), at, mode, current)
        for c in channels if c.device_id in active and c.device_id in devices and (c.introduced_at or c.created_at) <= at]
    return {"id": space.id, "name": space.name, "kind": space.kind, "campus_id": space.campus_id,
        "building_id": space.building_id, "floor_id": space.floor_id, "at": at, **_aggregate(states), "mode": mode,
        "mode_expires_at": expiry, "mode_reason": reason, "channels": states,
        "active_anomaly_ids": [], "planned_occupancy": None, "scheduled_titles": [], "control_authorization": False}


def snapshots(db, spaces, at=None):
    current = at is None
    at = aware(at) if at else utcnow()
    loaded = _load(db, spaces, at, at, latest_only=True)
    partitions = partition_evidence(loaded, spaces)
    rows = [_at(s, at, partitions[s.id], current) for s in spaces]
    lookup = {r["id"]: r for r in rows}
    channel_lookup = {c["channel_id"]: c for row in rows for c in row["channels"]}
    for hold in db.scalars(select(ChannelHold).where(ChannelHold.channel_id.in_(channel_lookup), ChannelHold.starts_at <= at, ChannelHold.ends_at > at).order_by(ChannelHold.ends_at)):
        channel_lookup[hold.channel_id]["manual_hold_until"] = hold.ends_at
        channel_lookup[hold.channel_id]["manual_hold_scope"] = "backend_edge"
    for alarm in db.scalars(select(RoomAnomaly).where(RoomAnomaly.space_id.in_(lookup), RoomAnomaly.episode_start <= at,
        or_(RoomAnomaly.resolved_at.is_(None), RoomAnomaly.resolved_at > at))):
        lookup[alarm.space_id]["active_anomaly_ids"].append(alarm.id)
    for event in db.scalars(select(ScheduleEvent).where(ScheduleEvent.space_id.in_(lookup), ScheduleEvent.status == "scheduled",
        ScheduleEvent.starts_at <= at, ScheduleEvent.ends_at > at)):
        row = lookup[event.space_id]
        row["scheduled_titles"].append(event.title)
        if event.planned_occupancy is not None:
            row["planned_occupancy"] = max(row["planned_occupancy"] or 0, event.planned_occupancy)
    return rows


def empty_durations():
    return {"occupancy": {k: 0. for k in ("occupied", "vacant", "unknown")},
        "lighting": {k: 0. for k in ("on", "off", "mixed", "unknown")},
        "sockets": {k: 0. for k in ("on", "off", "mixed", "unknown")},
        "mode": {k: 0. for k in ("manual", "automatic", "maintenance", "fault")},
        "observed_power_seconds": 0., "unknown_power_seconds": 0.}


def timeline(db, space, start, end, loaded=None):
    start, end = window(start, end)
    loaded = loaded or _load(db, [space], start, end)
    bindings, channels, devices, observations, modes = loaded
    # Scope once; distribution callers pass a pre-partitioned evidence set.
    if loaded.space_id != space.id:
        loaded = partition_evidence(loaded, [space])[space.id]
    cuts = {start, end}
    cuts.update(c.introduced_at or c.created_at for c in loaded[1] if start < (c.introduced_at or c.created_at) < end)
    for row in loaded[0]:
        cuts.update(t for t in (row.valid_from, row.valid_to) if t and start < t < end)
    for row in loaded[3]:
        cuts.update(t for t in (row.observed_at, row.valid_until) if start < t < end)
    for row in loaded[4]:
        cuts.update(t for t in (row.starts_at, row.ends_at) if t and start < t < end)
    cuts = sorted(cuts)
    if len(cuts) > 20000:
        raise DomainError("timeline_too_dense", "Reduce the interval to at most 20,000 change boundaries", 422)
    intervals, durations, sources = [], empty_durations(), set()
    for left, right in zip(cuts, cuts[1:]):
        state = _at(space, left, loaded)
        seconds = (right-left).total_seconds()
        interval = {"start": left, "end": right, "duration_seconds": seconds,
            **{k: state[k] for k in ("occupancy", "lighting", "lighting_verification_kind", "sockets", "observed_power_w", "power_coverage", "mode", "source_mode", "quality")},
            "observation_ids": [c["observation_id"] for c in state["channels"] if c["observation_id"] is not None and c["quality"] == "good"]}
        for key in ("occupancy", "lighting", "sockets", "mode"):
            durations[key][state[key]] += seconds
        durations["observed_power_seconds" if state["observed_power_w"] is not None else "unknown_power_seconds"] += seconds
        sources.add(state["source_mode"])
        intervals.append(interval)
    return {"room_id": space.id, "start": start, "end": end, "intervals": intervals, "durations": durations,
        "source_modes": sorted(sources), "semantics": "Half-open event-time intervals, cut at every observation, freshness expiry and historical binding; unknown is not vacant/off/zero. Planned occupancy never substitutes for observed presence."}


def distribution(db, spaces, group_by="building", at=None, start=None, end=None):
    if (start is None) != (end is None):
        raise DomainError("invalid_window", "Both start and end are required", 422)
    if start:
        start, end = window(start, end)
    moment = aware(at) if at else end or utcnow()
    states = snapshots(db, spaces, moment)
    model = {"campus": Campus, "building": Building, "floor": Floor}[group_by]
    names = {r.id: r.name for r in db.scalars(select(model))}
    groups = {}
    loaded = partition_evidence(_load(db, spaces, start, end), spaces) if start else None
    lookup = {s.id: s for s in spaces}
    for row in states:
        key = row[f"{group_by}_id"] or "unmapped"
        if key not in groups:
            groups[key] = {"id": key, "name": names.get(key, "未映射楼层"), "room_count": 0,
                "occupancy": {k: 0 for k in ("occupied", "vacant", "unknown")},
                "lighting": {k: 0 for k in ("on", "off", "mixed", "unknown")}, "sockets": {k: 0 for k in ("on", "off", "mixed", "unknown")},
                "observed_power_w": None, "known_power_rooms": 0, "durations": empty_durations() if start else None, "source_modes": set()}
        group = groups[key]
        group["room_count"] += 1
        if not start:
            group["source_modes"].add(row["source_mode"])
        for category in ("occupancy", "lighting", "sockets"):
            group[category][row[category]] += 1
        if row["observed_power_w"] is not None:
            group["observed_power_w"] = (group["observed_power_w"] or 0.) + row["observed_power_w"]
            group["known_power_rooms"] += 1
        if start:
            result = timeline(db, lookup[row["id"]], start, end, loaded[row["id"]])
            group["source_modes"].update(result["source_modes"])
            for k, v in result["durations"].items():
                if isinstance(v, dict):
                    for name, seconds in v.items():
                        group["durations"][k][name] += seconds
                else:
                    group["durations"][k] += v
    source_modes = sorted({mode for group in groups.values() for mode in group["source_modes"]})
    for group in groups.values():
        group["source_modes"] = sorted(group["source_modes"])
    return {"source_modes": source_modes, "at": moment, "start": start, "end": end, "group_by": group_by, "total_rooms": len(spaces), "groups": list(groups.values()),
        "semantics": "Counts include every authorized mapped room. Duration totals are room-seconds. Group power is an explicitly partial sum across known-power rooms, not billing energy."}
