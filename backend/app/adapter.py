"""Authenticated durable transport boundary shared by virtual and release-gated devices.
An MQTT PUBACK proves delivery only. A correlated fresh observation proves state, never
safe voltage absence. No network publishing happens inside this backend module.
"""
from datetime import timedelta
from sqlalchemy import select
from .common import DomainError, payload_hash, uid, audit
from .db import utcnow, iso
from .models import Device, Command, AdapterObservation, Telemetry, SimulatedOutput
from carbentra_iot_contract.plug_wire import validate_ack


def store_ack(db, raw, received_at=None, telemetry_id=None):
    from .control import TERMINAL, transition
    now = received_at or utcnow()
    try:
        validate_ack(raw, raw.get("device_id"))
    except (ValueError, KeyError, TypeError) as exc:
        raise DomainError("ack_schema_invalid", "Acknowledgement failed the canonical wire gate", 422, {"reason": str(exc)})
    db.flush()  # Do not overwrite uncommitted lifecycle transitions when refreshing locks
    device = db.scalar(select(Device).where(Device.id == raw["device_id"]).with_for_update().execution_options(populate_existing=True))
    if not device:
        raise DomainError("unknown_device", "Register device before acknowledging commands", 404)
    digest = payload_hash(raw)
    identity = (AdapterObservation.command_id == raw["id"], AdapterObservation.device_id == raw["device_id"], AdapterObservation.boot_epoch == raw["boot_epoch"], AdapterObservation.sequence == raw["seq"], AdapterObservation.status == raw["status"])
    old = db.scalar(select(AdapterObservation).where(*identity))
    if old:
        if old.payload_hash != digest:
            raise DomainError("ack_conflict", "Conflicting acknowledgement for the same transition identity", 409)
        return old, False
    command = db.scalar(select(Command).where(Command.id == raw["id"]).with_for_update().execution_options(populate_existing=True))
    matched = bool(command and command.device_id == device.id and str(command.sequence) == raw["seq"] and command.expected_boot_epoch == raw["boot_epoch"])
    observation = AdapterObservation(command_id=raw["id"], device_id=device.id, campus_id=device.campus_id, boot_epoch=raw["boot_epoch"], sequence=raw["seq"],
        status=raw["status"], source_mode=device.source_mode, payload_hash=digest, raw_payload=raw, received_at=now, matched=matched)
    db.add(observation)
    db.flush()
    if not matched or command.status in TERMINAL:
        return observation, True  # Preserve orphan/late evidence, never manufacture correlation.
    if now >= command.expires_at:
        transition(db, command, "timed_out", "Acknowledgement arrived after command deadline", {"observation_id": observation.id}, now)
        return observation, True
    if command.profile_revision != device.profile_revision:
        transition(db, command, "rejected" if command.status in {"requested", "dispatched"} else "failed", "Profile changed during execution", {"observation_id": observation.id}, now)
        return observation, True
    if command.status == "requested" and command.lease_id:
        # Broker receipt and device ACK travel through independent durable outboxes.
        # A correlated ACK can arrive first; it proves device reception, not success.
        transition(db, command, "dispatched", "Correlated device acknowledgement establishes delivery before broker receipt", {"observation_id": observation.id}, now)
    expected = command.history[0]["evidence"].get("desired_on")
    evidence = {"observation_id": observation.id, "boot_epoch": raw["boot_epoch"], "sequence": raw["seq"], "received_at": iso(now),
        "observed_monotonic_ms": raw.get("observed_monotonic_ms"), "source_mode": device.source_mode, "wire_status": raw["status"]}
    if telemetry_id is not None:
        sample = db.get(Telemetry, telemetry_id)
        if not sample or sample.device_id != device.id or sample.correlation_command_id != command.id or sample.observed_at <= command.issued_at or sample.received_at <= command.issued_at or sample.quality != "good":
            raise DomainError("observation_mismatch", "Correlated telemetry is absent, stale or invalid", 409)
        evidence["telemetry_id"] = telemetry_id
    if raw["status"] == "OBSERVED_VERIFIED" and command.dispatch_mode == "IN_PROCESS" and telemetry_id is None:
        raise DomainError("observation_required", "In-process verification requires an independent persisted telemetry observation", 409)
    if raw["status"] in {"REQUESTED_AWAITING_FEEDBACK", "ACCEPTED_NO_CHANGE"}:
        if command.status == "dispatched":
            transition(db, command, "acknowledged", "Device accepted request; observation not yet verified", evidence, now)
    elif raw["status"] == "OBSERVED_VERIFIED":
        if device.source_mode == "REAL":
            anchor = db.get(Telemetry, device.latest_telemetry_id) if device.latest_telemetry_id else None
            anchor_mono = anchor.raw_payload.get("monotonic_ms") if anchor else None
            observed_mono = raw.get("observed_monotonic_ms")
            fresh = False
            if anchor and anchor.boot_epoch == raw["boot_epoch"] and anchor.time_source == "authenticated" and anchor.quality == "good" and type(anchor_mono) is int and type(observed_mono) is int:
                observed_wall = anchor.observed_at + timedelta(milliseconds=observed_mono-anchor_mono)
                uncertainty = timedelta(milliseconds=anchor.time_uncertainty_ms or 0)
                fresh = command.issued_at-uncertainty <= observed_wall <= now+uncertainty and now-observed_wall <= timedelta(seconds=10)
                evidence["projected_observed_at"] = iso(observed_wall)
                evidence["time_anchor_telemetry_id"] = anchor.id
            if not fresh:
                if command.status in {"dispatched", "acknowledged"}:
                    transition(db, command, "failed", "Cannot establish fresh authenticated observation time; physical state remains unverified", evidence, now)
                return observation, True
        if raw["desired_on"] != expected or raw["output_present"] != expected:
            if command.status != "requested":
                transition(db, command, "failed", "Observation does not match authorized requested state", evidence, now)
        elif command.status in {"dispatched", "acknowledged"}:
            if command.status == "dispatched":
                transition(db, command, "acknowledged", "Terminal observation includes acceptance evidence", evidence, now)
            command.result = {"desired_on": raw["desired_on"], "output_present": raw["output_present"], "voltage_absence_proven": False,
                "simulated": device.source_mode == "SIMULATED", "observation_id": observation.id, "observed_at": iso(now), "boot_epoch": raw["boot_epoch"], "sequence": raw["seq"]}
            transition(db, command, "verified", "Fresh correlated adapter observation matched the authorized request", evidence, now)
            if command.action != "hold":
                device.last_control_at = now
    elif raw["status"] == "TIMED_OUT":
        transition(db, command, "timed_out", "Device observation deadline elapsed", evidence, now)
    elif raw["terminal"]:
        status = "rejected" if command.status in {"requested", "dispatched"} and raw["status"] not in {"FAILED_FEEDBACK", "FAILED_SUPERSEDED"} else "failed"
        if status == "failed" and command.status == "requested":
            status = "rejected"
        transition(db, command, status, raw["status"], evidence, now)
    return observation, True


def physical_released(device, settings, db=None, now=None):
    from .models import CommissioningRecord, Binding
    if not (settings.physical_dispatch_enabled and device.source_mode == "REAL" and device.dispatch_mode == "PHYSICAL" and device.physical_release_id
            and device.physical_release_id in settings.physical_release_ids and device.commissioned):
        return False
    if db is None:
        return False
    release = db.get(CommissioningRecord, device.physical_release_id)
    binding = db.scalar(select(Binding).where(Binding.device_id == device.id, Binding.valid_to.is_(None)).limit(1))
    return bool(release and binding and release.device_id == device.id and release.binding_id == binding.id and release.status == "released"
        and release.valid_until > (now or utcnow()) and release.profile_id == device.profile_id and release.load_id and release.load_name)


def poll_commands(db, settings, allowed_ids, limit=20, now=None):
    from .control import transition, eligibility
    now = now or utcnow()
    result = []
    commands = list(db.scalars(select(Command).where(Command.device_id.in_(allowed_ids), Command.dispatch_mode.in_(["VIRTUAL", "PHYSICAL"]), Command.status == "requested").order_by(Command.issued_at).with_for_update(skip_locked=True).limit(limit)))
    for command in commands:
        device = db.get(Device, command.device_id)
        if command.expires_at <= now:
            transition(db, command, "timed_out", "Expired before adapter lease", now=now)
            continue
        from .room_control import policy_command_block
        safety = eligibility(db, device, now, command.action, settings=settings, channel_id=command.channel_id) or policy_command_block(db, command, now)
        if command.profile_revision != device.profile_revision or safety:
            transition(db, command, "rejected", safety or "Device profile changed before dispatch", now=now)
            continue
        from .models import User
        actor = db.get(User, command.created_by)
        if not actor or not actor.enabled or actor.role not in {"admin", "operator"} or (actor.campus_ids is not None and command.campus_id not in actor.campus_ids):
            transition(db, command, "rejected", "Issuing actor authorization was revoked before dispatch", now=now)
            continue
        if command.dispatch_mode == "PHYSICAL" and not physical_released(device, settings, db, now):
            transition(db, command, "rejected", "Physical release gate is closed", now=now)
            continue
        if command.dispatch_mode == "VIRTUAL" and (device.source_mode != "SIMULATED" or device.dispatch_mode != "VIRTUAL"):
            transition(db, command, "rejected", "Virtual transport requires explicitly registered simulated device", now=now)
            continue
        if command.lease_id:
            # An unacknowledged delivery lease may have published before a crash. Never
            # reissue an action blindly; the edge durable inbox owns delivery reconciliation.
            if command.lease_expires_at <= now:
                transition(db, command, "rejected", "Adapter lease expired; delivery may be unknown, no automatic replay", now=now)
            continue
        command.lease_id = uid("lease")
        command.lease_expires_at = min(command.expires_at, now+timedelta(seconds=30))
        item = {"id": command.id, "device_id": command.device_id, "channel_id": command.channel_id, "channel_key": command.channel_key,
            "product_family": command.product_family, "source_mode": device.source_mode, "dispatch_mode": command.dispatch_mode, "transport": "MQTT",
            "lease_id": command.lease_id, "lease_expires_at": iso(command.lease_expires_at),
            "release_id": device.physical_release_id if command.dispatch_mode == "PHYSICAL" else None}
        if command.product_family == "SWITCH":
            canonical = {"schema_version":1,"id":command.id,"device_id":command.device_id,"product_family":"SWITCH",
                "channel_id":command.channel_key,"capability":"relay.commanded","value":command.history[0]["evidence"]["desired_on"],
                "sequence":str(command.sequence),"issued_at":iso(command.issued_at),"expires_at":iso(min(command.expires_at,command.lease_expires_at)),
                "boot_id":command.expected_boot_epoch,"source_mode":command.source_mode,
                "authority":{"kind":"manual" if command.manual_hold_seconds else "cloud","lease_id":command.lease_id,"lease_expires_at":iso(command.lease_expires_at)}}
            if command.manual_hold_seconds:
                canonical["manual_hold_seconds"] = command.manual_hold_seconds
            from .iot_ingestion import contract
            contract().validate_command(canonical)
            item["canonical_command"] = canonical
        else:
            item["wire"] = {"id": command.id, "device_id": command.device_id, "profile_id": device.profile_id, "seq": str(command.sequence),
                "issued_s": int(command.issued_at.timestamp()), "expires_s": int(command.expires_at.timestamp()), "action": command.action}
        result.append(item)
        audit(db, "adapter", "leased", "command", command.id, {"source_mode": device.source_mode, "dispatch_mode": command.dispatch_mode})
    return result


def record_delivery(db, command_id, body, allowed_ids, now=None):
    from .control import transition, TERMINAL
    now = now or utcnow()
    command = db.scalar(select(Command).where(Command.id == command_id).with_for_update().execution_options(populate_existing=True))
    if not command or command.device_id not in allowed_ids:
        raise DomainError("not_found", "Leased command not found", 404)
    if command.lease_id != body.lease_id:
        raise DomainError("lease_mismatch", "Delivery receipt does not match the outstanding lease", 409)
    incoming = body.model_dump()
    if command.delivery_receipt and command.delivery_receipt["payload"] != incoming:
        raise DomainError("delivery_conflict", "The leased delivery receipt already contains different content", 409)
    if not command.delivery_receipt:
        command.delivery_receipt = {"payload": incoming, "received_at": iso(now)}
    if command.status == "requested":
        if now >= command.expires_at or body.status == "expired":
            transition(db, command, "timed_out", "Command expired before confirmed delivery", now=now)
        elif body.status == "failed":
            transition(db, command, "rejected", body.reason or "Adapter could not establish delivery; device state is unknown", {"delivery_state_unknown": True}, now)
        else:
            transition(db, command, "dispatched", "MQTT publish acknowledged; actuation is not verified", {"transport": "MQTT", "lease_id": body.lease_id}, now)
    return {"id": command.id, "seq": str(command.sequence), "status": command.status, "durable": True}
