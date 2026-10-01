from sqlalchemy import select, func
from .common import DomainError, require_entity, record_dict, audit
from .db import utcnow
from .models import Campus, Building, Floor, Space, Circuit, Device, Binding, Telemetry, State


def validate_binding(db, values):
    campus = require_entity(db, Campus, values["campus_id"])
    building = require_entity(db, Building, values["building_id"]) if values.get("building_id") else None
    floor = require_entity(db, Floor, values["floor_id"]) if values.get("floor_id") else None
    space = require_entity(db, Space, values["space_id"]) if values.get("space_id") else None
    circuit = require_entity(db, Circuit, values["circuit_id"]) if values.get("circuit_id") else None
    if building and building.campus_id != campus.id:
        raise DomainError("binding_mismatch", "Building does not belong to campus", 409)
    if floor and (not building or floor.building_id != building.id):
        raise DomainError("binding_mismatch", "Floor does not belong to the selected building", 409)
    if space and (not building or space.building_id != building.id or space.campus_id != campus.id or (space.floor_id and space.floor_id != values.get("floor_id"))):
        raise DomainError("binding_mismatch", "Space does not match campus, building and floor", 409)
    if circuit and (circuit.campus_id != campus.id or circuit.building_id != values.get("building_id") or (circuit.space_id and circuit.space_id != values.get("space_id"))):
        raise DomainError("binding_mismatch", "Circuit does not match the selected spatial scope", 409)
    return values


def add_binding(db, device, actor, reason, at=None):
    at = at or utcnow()
    for old in db.scalars(select(Binding).where(Binding.device_id == device.id, Binding.valid_to.is_(None))).all():
        old.valid_to = at
    binding = Binding(device_id=device.id, valid_from=at, reason=reason, actor=actor,
                      **{key: getattr(device, key) for key in ("campus_id", "building_id", "floor_id", "space_id", "circuit_id")})
    db.add(binding)
    from .models import ForecastProjectionState, DeviceChannel
    for channel in db.scalars(select(DeviceChannel).where(DeviceChannel.device_id == device.id)):
        channel.campus_id = device.campus_id
    projection = db.get(ForecastProjectionState, device.id)
    if projection:
        projection.campus_id = device.campus_id
    db.flush()
    return binding


def freshness_limits(db, settings):
    stored = db.get(State, "settings")
    values = stored.value if stored else {}
    return values.get("stale_after_seconds", settings.stale_after_seconds), values.get("offline_after_seconds", settings.offline_after_seconds)


def device_status(device, settings, now=None, limits=None):
    if not device.last_seen_at:
        return "unknown"
    seconds = ((now or utcnow()) - device.last_seen_at).total_seconds()
    stale, offline = limits or (settings.stale_after_seconds, settings.offline_after_seconds)
    if seconds > offline:
        return "offline"
    if seconds > stale:
        return "stale"
    return "online"


def telemetry_dict(sample):
    return record_dict(sample, exclude=("raw_payload", "payload_hash"))


def device_dict(db, device, settings, latest=None, limits=None):
    result = record_dict(device, exclude=("latest_telemetry_id", "last_control_at", "next_command_sequence"))
    result["status"] = device_status(device, settings, limits=limits)
    sample = latest if latest is not None else (db.get(Telemetry, device.latest_telemetry_id) if device.latest_telemetry_id else None)
    result["latest"] = telemetry_dict(sample) if sample else None
    return result


def device_list(db, devices, settings):
    ids = [d.latest_telemetry_id for d in devices if d.latest_telemetry_id]
    samples = {x.id: x for x in db.scalars(select(Telemetry).where(Telemetry.id.in_(ids))).all()} if ids else {}
    limits = freshness_limits(db, settings)
    return [device_dict(db, d, settings, samples.get(d.latest_telemetry_id), limits) for d in devices]


def create_device(db, values, actor):
    if db.get(Device, values["id"]):
        raise DomainError("already_exists", "Device identity already exists", 409)
    validate_binding(db, values)
    if values.get("circuit_id") and db.get(Circuit, values["circuit_id"]).source_mode != values["source_mode"]:
        raise DomainError("source_mode_mismatch", "Device and electrical boundary must have the same source mode", 409)
    if values["source_mode"] != "SIMULATED" and values.get("allow_control"):
        raise DomainError("physical_control_disabled", "Only simulated devices may be enabled for control", 409)
    if values.get("critical") and values.get("allow_control"):
        raise DomainError("critical_load", "Critical loads cannot be control-enabled", 409)
    device = Device(**values, provenance={"origin": "operator_registry", "measurement_claim": False}, profile_id="simulated-controllable-v1" if values["source_mode"] == "SIMULATED" else "unassigned")
    db.add(device)
    db.flush()
    if device.kind == "meter" and device.circuit_id:
        circuit = db.get(Circuit, device.circuit_id)
        if circuit.meter_device_id:
            raise DomainError("meter_conflict", "Circuit already has a primary meter", 409)
        circuit.meter_device_id = device.id
    add_binding(db, device, actor, "Initial device registration")
    audit(db, actor, "created", "device", device.id, {"source_mode": device.source_mode})
    return device
