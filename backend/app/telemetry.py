"""Durable idempotent ingestion. Reception and accounting eligibility are separate."""
from datetime import timedelta, datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .common import DomainError, payload_hash, audit
from .db import utcnow, iso
from .models import Device, Telemetry, Binding, Alarm, Event
from .schemas import TelemetryIn


def quality_for(sample, received_at):
    flags = []
    if sample.counter_scope == "import_only":
        flags.append("EXPORT_UNAVAILABLE")
    if not sample.valid:
        flags.append("MEASUREMENT_INVALID")
    if not sample.calibrated:
        flags.append("UNCALIBRATED")
    if sample.energy_status != "known":
        flags.append("ENERGY_UNCERTAIN")
    if sample.time_source == "received_only" or sample.observed_at is None or sample.time_uncertainty_ms is None or sample.time_uncertainty_ms > 5000:
        flags.append("TIME_UNCERTAIN")
    if sample.observed_at and sample.observed_at > received_at + timedelta(seconds=5):
        flags.append("FUTURE_TIMESTAMP")
    if sample.fault_latched:
        flags.append("FAULT_LATCHED")
    return flags


def ingest_sample(db, sample, raw_payload=None, received_at=None, actor="adapter"):
    db.flush()  # Preserve intentional in-transaction registry changes before refreshing locks
    received_at = received_at or utcnow()
    payload = raw_payload or sample.model_dump(mode="json")
    digest = payload_hash(payload)
    identity = (Telemetry.device_id == sample.device_id, Telemetry.boot_epoch == sample.boot_epoch, Telemetry.sample_seq == sample.sample_seq)
    existing = db.scalar(select(Telemetry).where(*identity))
    if existing:
        if existing.payload_hash != digest:
            raise DomainError("telemetry_conflict", "Duplicate sample identity contains different content", 409, {"device_id": sample.device_id, "boot_epoch": sample.boot_epoch, "sample_seq": sample.sample_seq})
        return existing, False
    device = db.scalar(select(Device).where(Device.id == sample.device_id).with_for_update().execution_options(populate_existing=True))
    if not device:
        raise DomainError("unknown_device", "Register and bind device before ingesting telemetry", 404)
    if device.source_mode != sample.source_mode:
        raise DomainError("source_mode_mismatch", "Measurement source must match the registered device", 409)
    observed_at = sample.observed_at if sample.time_source != "received_only" and sample.observed_at else received_at
    flags = quality_for(sample, received_at)
    prior_latest = db.get(Telemetry, device.latest_telemetry_id) if device.latest_telemetry_id else None
    if prior_latest and prior_latest.boot_epoch == sample.boot_epoch:
        sequence_direction = int(sample.sample_seq) - int(prior_latest.sample_seq)
        time_direction = (observed_at-prior_latest.observed_at).total_seconds()
        if sequence_direction * time_direction < 0:
            flags.append("SEQUENCE_TIME_CONFLICT")
    binding = db.scalar(select(Binding).where(Binding.device_id == device.id, Binding.valid_from <= observed_at,
        (Binding.valid_to.is_(None)) | (Binding.valid_to > observed_at)).order_by(Binding.valid_from.desc()).limit(1))
    if not binding:
        flags.append("BINDING_UNKNOWN")
    elif binding.valid_to is None and any(getattr(device, key) != getattr(binding, key) for key in ("campus_id", "building_id", "floor_id", "space_id", "circuit_id")):
        flags.append("REGISTRY_BINDING_MISMATCH")
    owner = binding or device
    values = sample.model_dump(exclude={"observed_at", "valid", "calibrated", "energy_status", "energy_uncertain_intervals", "counter_scope"})
    record = Telemetry(**values, raw_payload=payload, payload_hash=digest, observed_at=observed_at, received_at=received_at,
        quality="good" if not flags else "invalid" if "MEASUREMENT_INVALID" in flags else "uncertain", quality_flags=flags,
        campus_id=owner.campus_id, building_id=owner.building_id, space_id=owner.space_id, circuit_id=owner.circuit_id, binding_id=binding.id if binding else None)
    # The savepoint confines a racing duplicate conflict to this insert.
    try:
        with db.begin_nested():
            db.add(record)
            db.flush()
    except IntegrityError:
        existing = db.scalar(select(Telemetry).where(*identity))
        if existing is None or existing.payload_hash != digest:
            raise DomainError("telemetry_conflict", "Conflicting concurrent duplicate sample", 409)
        return existing, False
    latest = prior_latest
    newer = not latest or (record.boot_epoch == latest.boot_epoch and int(record.sample_seq) > int(latest.sample_seq) and record.observed_at >= latest.observed_at) or (record.boot_epoch != latest.boot_epoch and record.observed_at > latest.observed_at)
    if newer and "SEQUENCE_TIME_CONFLICT" not in record.quality_flags:
        device.latest_telemetry_id = record.id
    # Last seen means reception, not proof of fresh observations.
    device.last_seen_at = max(device.last_seen_at or received_at, received_at)
    if sample.fault_latched:
        current_evidence = device.latest_telemetry_id == record.id and binding is not None and binding.valid_to is None and sample.time_source != "received_only" and -5 <= (received_at-record.observed_at).total_seconds() <= 120
        if current_evidence:
            current = db.scalar(select(Alarm).where(Alarm.device_id == device.id, Alarm.type == "local_fault", Alarm.status != "resolved"))
            if not current:
                from .common import uid
                db.add(Alarm(id=uid("alarm"), device_id=device.id, campus_id=record.campus_id, building_id=record.building_id, space_id=record.space_id,
                    type="local_fault", severity="critical", title=f"{device.name} · 本地故障锁存", description="Fresh device evidence reports a latched local fault. De-energized/safe-to-touch is not established.", source_mode=record.source_mode,
                    notes=[{"at": iso(received_at), "by": actor, "text": f"Observed {iso(record.observed_at)}; telemetry {record.id}; boot {record.boot_epoch}; no voltage-absence proof"}]))
        else:
            db.add(Event(type="telemetry.historical_or_unattributed_fault", entity_id=str(record.id), campus_id=record.campus_id))
    from .classrooms import mirror_telemetry
    mirror_telemetry(db, record)
    from .projection import mark_observation
    mark_observation(db,device,record)
    return record, True


def ingest_batch(db, samples, allowed_ids=None):
    results = []
    changed_campuses = set()
    for sample in samples:
        if allowed_ids is not None and sample.device_id not in allowed_ids:
            raise DomainError("adapter_scope_denied", "Adapter is not authorized for this device identity", 403)
        record, created = ingest_sample(db, sample)
        if created:
            changed_campuses.add(record.campus_id)
        results.append({"device_id": record.device_id, "boot_epoch": record.boot_epoch, "sample_seq": record.sample_seq, "telemetry_id": record.id, "status": "stored" if created else "duplicate", "quality": record.quality, "quality_flags": record.quality_flags})
    for campus_id in changed_campuses:
        db.add(Event(type="telemetry.ingested", entity_id="batch", campus_id=campus_id))
    db.commit()  # Receipt never precedes durable commit.
    return {"receipts": results, "stored": sum(x["status"] == "stored" for x in results), "duplicates": sum(x["status"] == "duplicate" for x in results), "durable": True}


def normalize_firmware(raw, source_mode="REAL", source_version="carbentra-wire-v2"):
    """V2 firmware wire adapter; raw evidence is retained unchanged by the caller."""
    from carbentra_iot_contract.plug_wire import validate_telemetry
    try:
        validate_telemetry(raw, raw.get("device_id"))
    except (ValueError, TypeError, KeyError) as exc:
        raise DomainError("wire_schema_invalid", "Firmware wire contract rejected the sample", 422, {"reason": str(exc)})
    quality = raw.get("time_quality")
    lower, upper = raw.get("unix_lower_s"), raw.get("unix_upper_s")
    unix_s = raw.get("unix_s")
    observed, uncertainty, time_source = None, None, "received_only"
    if quality == "authenticated":
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in (lower, upper, unix_s)) or not lower <= unix_s <= upper or upper - lower > 5:
            raise DomainError("wire_time_invalid", "Authenticated time requires consistent bounds <=5 seconds", 422)
        try:
            observed = datetime.fromtimestamp(unix_s, timezone.utc)
        except (ValueError, OverflowError, OSError):
            raise DomainError("wire_time_invalid", "Invalid authenticated UTC timestamp", 422)
        uncertainty, time_source = (upper - lower) * 1000, "authenticated"
    elif quality != "unknown":
        raise DomainError("wire_time_invalid", "Unsupported time_quality", 422)
    status = raw.get("energy_status", "unknown")
    known = status == "calibrated_counts_known_intervals_since_boot_not_billing_certified"
    return TelemetryIn(device_id=raw["device_id"], boot_epoch=raw["boot_epoch"], sample_seq=raw["sample_seq"], observed_at=observed,
        time_source=time_source, time_uncertainty_ms=uncertainty, active_power_w=raw.get("active_w"), voltage_v=raw.get("voltage_v"), current_a=raw.get("current_a"),
        energy_import_wh=raw.get("known_forward_wh_since_boot"), energy_export_wh=raw.get("known_reverse_wh_since_boot"),
        board_temperature_c=raw.get("board_temperature_c") if raw.get("board_temperature_valid") else None,
        desired_on=raw.get("desired_on"), output_present=raw.get("output_present") if raw.get("feedback_valid") else None,
        fault_latched=raw.get("fault_latched"), valid=raw["valid"], calibrated=raw["calibrated"],
        energy_status="known" if known else "uncertain" if "uncertain" in str(status).lower() else "unknown",
        energy_uncertain_intervals=raw.get("energy_uncertain_intervals", 0), source_mode=source_mode, source_version=source_version)
