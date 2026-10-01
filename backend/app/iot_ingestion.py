"""Canonical three-product ingest adapters with a single authoritative energy ledger."""
from collections import defaultdict
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from .models import Device, Binding, DeviceChannel, HardwareEvent, ChannelAcknowledgement, Event, Command
from .common import DomainError, require_entity, payload_hash
from .db import utcnow
from .classrooms import ingest_channel
from .classroom_schemas import ChannelSample, ChannelValue

def contract():
    import carbentra_iot_contract
    return carbentra_iot_contract


def _ensure_channels(db, device, event):
    grouped = defaultdict(list)
    for reading in event["readings"]:
        grouped[reading["channel_id"]].append(reading)
    channels = {c.channel_key: c for c in db.scalars(select(DeviceChannel).where(DeviceChannel.device_id == device.id))}
    for key, readings in grouped.items():
        caps = {r["capability"] for r in readings}
        kind = ("socket" if event["product_family"] == "PLUG" else "lighting") if caps & {"relay.commanded", "relay.feedback"} else (
            "presence" if caps & {"presence.pir", "presence.radar"} else "illuminance" if "illuminance.raw" in caps else "power" if "power.active" in caps else None)
        if kind is None:
            continue  # Health, local button and control-mode details remain in raw immutable events.
        if key not in channels:
            supported = sorted({r["capability"] for r in readings if r["quality"] != "unavailable"})
            channels[key] = DeviceChannel(id=f"{device.id}:{key}", device_id=device.id, campus_id=device.campus_id,
                channel_key=key, name=f"{device.name} · {key}", kind=kind, capabilities=supported,
                unit="raw_count" if kind == "illuminance" else "W" if kind == "power" else None,
                freshness_seconds=120, controllable=device.source_mode == "SIMULATED" and device.allow_control and kind == "lighting" and "relay.commanded" in supported)
            db.add(channels[key])
        elif channels[key].kind != kind:
            raise DomainError("channel_kind_conflict", "Event changes a registered channel's kind", 409)
    db.flush()
    return grouped, channels


def ingest_event(db, body, now=None):
    now = now or utcnow()
    try:
        contract().validate_event(body)
    except (ValueError, TypeError, KeyError) as exc:
        raise DomainError("iot_schema_invalid", "Canonical event rejected", 422, {"reason": str(exc)})
    identity = (HardwareEvent.device_id == body["device_id"], HardwareEvent.boot_id == body["boot_id"], HardwareEvent.sequence == body["sequence"])
    digest = payload_hash(body)
    existing = db.scalar(select(HardwareEvent).where(*identity))
    if existing:
        if existing.payload_hash != digest:
            raise DomainError("event_conflict", "Event identity contains different content", 409)
        return existing, False
    device = require_entity(db, Device, body["device_id"])
    if device.source_mode != body["source_mode"]:
        raise DomainError("source_mode_mismatch", "Event source differs from the registered device", 409)
    expected = {"smart_plug": "PLUG", "switch": "SWITCH", "light": "SWITCH", "presence": "PRESENCE"}.get(device.kind)
    if expected and expected != body["product_family"]:
        raise DomainError("product_family_mismatch", "Event family differs from registered device", 409)
    observed = contract().timestamp(body["observed_at"]) if body["observed_at"] else None
    binding = db.scalar(select(Binding).where(Binding.device_id == device.id, Binding.valid_from <= (observed or now),
        or_(Binding.valid_to.is_(None), Binding.valid_to > (observed or now))).order_by(Binding.valid_from.desc()).limit(1))
    row = HardwareEvent(id=body["event_id"], device_id=device.id, campus_id=binding.campus_id if binding else device.campus_id,
        boot_id=body["boot_id"], sequence=body["sequence"], observed_at=observed, server_received_at=now,
        source_mode=body["source_mode"], payload_hash=digest, raw_payload=body)
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        existing = db.scalar(select(HardwareEvent).where(*identity))
        if existing and existing.payload_hash == digest:
            return existing, False
        raise DomainError("event_conflict", "Concurrent event identity conflict", 409)
    grouped, channels = _ensure_channels(db, device, body)
    telemetry = None
    if body["source_protocol"] == "plug-wire-v2":
        from .telemetry import normalize_firmware, ingest_sample
        sample = normalize_firmware(body["raw"], source_mode=body["source_mode"])
        # Ingest against the wire payload hash used by the old compatibility route,
        # so crossing adapter paths remains a genuine idempotent retry.
        telemetry, stored = ingest_sample(db, sample, raw_payload=body["raw"], received_at=now)
        if not stored:
            from .classrooms import mirror_telemetry
            mirror_telemetry(db, telemetry)
    if body["product_family"] == "SWITCH" and "meter.aggregate" in grouped:
        store_switch_aggregate(db, device, body, now)
    for key, readings in grouped.items():
        channel = channels.get(key)
        if not channel:
            continue
        # Plug relay and power state already projected from validated wire evidence.
        if telemetry and channel.kind in {"socket", "lighting", "power"}:
            continue
        usable = {r["capability"]: r["value"] for r in readings if r["quality"] == "valid"}
        values = {}
        if channel.kind == "presence":
            if usable.get("presence.pir") is True or usable.get("presence.radar") is True:
                values["occupancy"] = "occupied"
            elif usable.get("presence.radar") is False:
                values["occupancy"] = "vacant"
            else:
                values["occupancy"] = "unknown"
        elif channel.kind in {"socket", "lighting"}:
            values = {"desired_on": usable.get("relay.commanded"), "output_present": usable.get("relay.feedback")}
            if body["product_family"] == "SWITCH":
                values["actuator_reported_on"] = usable.get("relay.commanded")
                values["fault_latched"] = body["raw"].get("fault_latched") if type(body["raw"].get("fault_latched")) is bool else None
        elif channel.kind == "power":
            values["active_power_w"] = usable.get("power.active")
        elif channel.kind == "illuminance":
            values["number"] = usable.get("illuminance.raw")
        trusted = body["time_quality"] == "authenticated"
        sample = ChannelSample(channel_id=channel.id, boot_epoch=body["boot_id"], sample_seq=body["sequence"], observed_at=observed,
            time_source="authenticated" if trusted else "device_clock" if observed else "received_only",
            time_uncertainty_ms=0. if trusted else None, source_mode=body["source_mode"], source_version=body["source_protocol"],
            valid=body["quality"] in {"valid", "partial"} and bool(usable), value=ChannelValue(**values))
        relative = None
        if body["source_protocol"] == "presence-gatt-v1" and not observed:
            reading = next((r for r in readings if r["capability"] == "presence.radar" and r["quality"] == "valid"), None)
            details = reading.get("details", {}) if reading else {}
            age = details.get("measurement_age_ms")
            gateway_at = contract().timestamp(body["received_at"])
            upload_seconds = (now-gateway_at).total_seconds()
            if (details.get("authenticity") == "authenticated_gatt_hmac_sha256" and details.get("continuous_occupancy") is True
                and type(age) in (int,float) and 0 <= age < min(channel.freshness_seconds*1000, 5000)
                and -1 <= upload_seconds <= 5):
                bounded_age = float(age)+max(0.,upload_seconds)*1000+1000.  # admitted gateway clock skew budget
                if bounded_age < min(channel.freshness_seconds*1000,5000):
                    relative = {"knowledge_at":now,"measurement_age_ms":bounded_age,"maximum_age_ms":5000}
        ingest_channel(db, sample, received_at=now, event_id=row.id, relative_proof=relative)
    db.add(Event(type="iot.ingested", entity_id=row.id, campus_id=row.campus_id))
    return row, True


def ingest_switch_ack(db, body, now=None):
    db.flush()  # Preserve pending ledger transitions before populate_existing locks.
    now = now or utcnow()
    try:
        contract().validate_switch_ack(body)
    except (ValueError, TypeError, KeyError) as exc:
        raise DomainError("iot_ack_schema_invalid", "Switch ACK rejected", 422, {"reason": str(exc)})
    device = require_entity(db, Device, body["device_id"])
    if device.kind not in {"switch", "light"}:
        raise DomainError("product_family_mismatch", "Channel ACK requires a Switch registry identity", 409)
    identity = (ChannelAcknowledgement.device_id == device.id, ChannelAcknowledgement.boot_id == body["boot_id"],
        ChannelAcknowledgement.command_id == body["id"], ChannelAcknowledgement.sequence == body["seq"],
        ChannelAcknowledgement.channel_number == body["channel"], ChannelAcknowledgement.result == body["result"])
    digest = payload_hash(body)
    old = db.scalar(select(ChannelAcknowledgement).where(*identity))
    if old:
        if old.payload_hash != digest:
            raise DomainError("ack_conflict", "Channel ACK identity has different content", 409)
        return old, False
    command = db.scalar(select(Command).where(Command.id == body["id"]).with_for_update().execution_options(populate_existing=True))
    matched = bool(command and command.device_id == device.id and command.product_family == "SWITCH" and command.expected_boot_epoch == body["boot_id"]
        and str(command.sequence) == body["seq"] and command.channel_key == f"relay.{body['channel']}")
    row = ChannelAcknowledgement(matched=matched, device_id=device.id, campus_id=device.campus_id, boot_id=body["boot_id"], command_id=body["id"],
        sequence=body["seq"], channel_number=body["channel"], result=body["result"], received_at=now, payload_hash=digest, raw_payload=body)
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        old = db.scalar(select(ChannelAcknowledgement).where(*identity))
        if old and old.payload_hash == digest:
            return old, False
        raise DomainError("ack_conflict", "Concurrent channel ACK conflict", 409)
    from .control import transition, TERMINAL
    if row.matched and command.status not in TERMINAL:
        evidence = {"channel_ack_id":row.id,"channel_id":command.channel_id,"channel_key":command.channel_key,
            "boot_epoch":row.boot_id,"sequence":row.sequence,"physical_verification":False,
            "verification_kind":"actuator_reported_only","server_received_at":__import__('app.db',fromlist=['iso']).iso(now)}
        if now >= command.expires_at:
            transition(db,command,"timed_out","Switch ACK arrived after command expiry; no physical state was verified",evidence,now)
        elif command.profile_revision != device.profile_revision:
            transition(db,command,"rejected" if command.status in {"requested","dispatched"} else "failed","Device profile changed before Switch acknowledgement",evidence,now)
        elif command.status == "requested" and not command.lease_id:
            pass  # An orphan ACK cannot establish an unleased cloud command's delivery.
        else:
            if command.status == "requested":
                transition(db,command,"dispatched","Correlated channel ACK establishes device delivery",evidence,now)
            if row.result == "commanded":
                evidence["actuator_reported_on"] = command.history[0]["evidence"]["desired_on"]
                transition(db,command,"acknowledged_unverified","Device reports channel execution; lamp/load state has no independent feedback",evidence,now)
                if command.action != "hold" and command.channel_id:
                    require_entity(db,DeviceChannel,command.channel_id).last_control_at=now
            else:
                transition(db,command,"rejected" if command.status in {"requested","dispatched"} else "failed",f"Switch rejected channel request: {row.result}",evidence,now)
    # No physical verification transition: actual Switch hardware has no load feedback.
    db.add(Event(campus_id=device.campus_id, type="channel.acknowledged_without_physical_verification", entity_id=str(row.id)))
    return row, True


def store_switch_aggregate(db, device, event, received_at):
    """One aggregate power/import-counter projection into the existing Telemetry ledger.
    Missing export and partial energy stay null/uncertain, never fabricated zero.
    """
    from .schemas import TelemetryIn
    from .telemetry import ingest_sample
    values={r["capability"]:r["value"] for r in event["readings"] if r["channel_id"]=="meter.aggregate" and r["quality"] in {"valid","partial"}}
    meter=event["raw"].get("aggregate_meter",{})
    power,voltage,current,energy=(values.get(k) for k in ("power.active","voltage.rms","current.rms","energy.import"))
    observed=contract().timestamp(event["observed_at"]) if event["observed_at"] else None
    sample=TelemetryIn(device_id=device.id,boot_epoch=event["boot_id"],sample_seq=event["sequence"],observed_at=observed,
        time_source="authenticated" if event["time_quality"]=="authenticated" else "received_only",time_uncertainty_ms=0. if event["time_quality"]=="authenticated" else None,
        active_power_w=power,voltage_v=voltage,current_a=current,energy_import_wh=energy,energy_export_wh=None,
        fault_latched=event["raw"].get("fault_latched"),valid=all(v is not None for v in (power,voltage,current,energy)),
        calibrated=meter.get("quality")=="calibrated_readback",energy_status="uncertain",counter_scope="import_only",
        energy_uncertain_intervals=meter.get("unknown_intervals",0),source_mode=event["source_mode"],source_version=event["source_protocol"])
    raw={**event,"counter_scope":"import_only","energy_uncertain_intervals":sample.energy_uncertain_intervals,
        "projection_basis":"one three-output aggregate; partial import counter; export unavailable"}
    return ingest_sample(db,sample,raw_payload=raw,received_at=received_at)
