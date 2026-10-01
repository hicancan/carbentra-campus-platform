"""Durable command ledger with simulation and explicitly release-gated adapter transport."""
from datetime import timedelta
import re
from sqlalchemy import select, case, or_
from .common import DomainError, uid, audit, payload_hash, record_dict
from .db import utcnow, iso
from .models import Device, Telemetry, Command, Strategy, Evaluation, Binding, User

TERMINAL = {"verified", "acknowledged_unverified", "rejected", "failed", "timed_out"}
TRANSITIONS = {
    "requested": {"dispatched", "rejected", "timed_out"},
    "dispatched": {"acknowledged", "acknowledged_unverified", "rejected", "failed", "timed_out"},
    "acknowledged": {"verified", "acknowledged_unverified", "failed", "timed_out"},
}


def command_dict(command):
    result = record_dict(command, exclude=("payload_hash", "updated_at"))
    result["sequence"] = str(result["sequence"])
    return result


def eligibility(db, device, now=None, action="shed", ignore_dwell=False, settings=None, channel_id=None):
    now = now or utcnow()
    from .adapter import physical_released
    if device.source_mode != "SIMULATED" and not (settings and physical_released(device, settings, db, now)):
        return "physical_control_disabled"
    if device.dispatch_mode == "DISABLED":
        return "control_not_authorized"
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,47}", device.id) or not re.fullmatch(r"[A-Za-z0-9_-]{1,47}", device.profile_id):
        return "wire_identity_unsupported"
    if not device.commissioned:
        return "not_commissioned"
    if device.critical:
        return "critical_load"
    if not device.allow_control:
        return "control_not_authorized"
    if action not in device.capabilities:
        return "unsupported_capability"
    if device.space_id:
        from .classrooms import effective_mode
        room_mode = effective_mode(db, device.space_id, now)[0]
        if room_mode in {"maintenance", "fault"}:
            return f"room_{room_mode}_interlock"
    from .scheduling import control_block
    maintenance = control_block(db, device, now)
    if maintenance:
        return maintenance
    from .channel_control import target_channel, switch_gate
    try:
        channel = target_channel(db, device, channel_id)
    except DomainError as exc:
        return exc.code
    if device.kind in {"switch", "light"}:
        return switch_gate(db, device, channel, now, ignore_dwell)
    if channel and (channel.channel_key != "relay.1" or not channel.controllable):
        return "unsupported_channel_capability"
    latest = db.get(Telemetry, device.latest_telemetry_id) if device.latest_telemetry_id else None
    freshness_limit = 10 if device.dispatch_mode in {"VIRTUAL", "PHYSICAL"} else 120
    age = (now-latest.observed_at).total_seconds() if latest else None
    if not latest or latest.quality != "good" or age > freshness_limit or age < -5:
        return "stale_or_invalid_observation"
    binding = db.scalar(select(Binding).where(Binding.device_id == device.id, Binding.valid_to.is_(None)).limit(1))
    if not binding or latest.binding_id != binding.id:
        return "observation_binding_mismatch"
    if any(getattr(device, key) != getattr(binding, key) for key in ("campus_id", "building_id", "floor_id", "space_id", "circuit_id")):
        return "registry_binding_mismatch"
    if device.source_mode == "REAL" and (latest.source_mode != "REAL" or age < 0):
        return "invalid_physical_observation"
    if latest.fault_latched:
        return "local_fault"
    if latest.fault_latched is None or latest.output_present is None or latest.desired_on is None:
        return "unknown_feedback_state"
    if device.source_mode == "REAL" and latest.time_source != "authenticated":
        return "untrusted_physical_time"
    if not ignore_dwell and device.last_control_at and (now-device.last_control_at).total_seconds() < device.minimum_dwell_seconds:
        return "minimum_dwell"
    return None


def transition(db, command, status, reason, evidence=None, now=None):
    if status not in TRANSITIONS.get(command.status, set()):
        raise DomainError("invalid_transition", f"Cannot transition {command.status} to {status}", 409)
    now = now or utcnow()
    evidence = dict(evidence or {})
    # Ledger transitions are causal even if the host clock is corrected backwards.
    # Preserve the measured processing time as evidence instead of silently claiming
    # the transition preceded the request or a previously persisted transition.
    causal_floor = max(command.issued_at, command.updated_at or command.issued_at)
    if now < causal_floor:
        evidence["processing_clock_at"] = iso(now)
        now = causal_floor
    command.status = status
    command.updated_at = now
    command.history = [*command.history, {"status": status, "at": iso(now), "reason": reason, "evidence": evidence}]
    audit(db, "control-service", status, "command", command.id, {"device_id": command.device_id, "simulated": command.source_mode == "SIMULATED", "reason": reason})


def create_command(db, body, key, actor, now=None, settings=None):
    db.flush()
    if not key or not 8 <= len(key) <= 160 or any(ord(x) < 33 or ord(x) > 126 for x in key):
        raise DomainError("idempotency_key_required", "Supply an 8–160 character Idempotency-Key header", 422)
    digest = payload_hash(body.model_dump(exclude={k for k in ("channel_id","manual_hold_seconds") if getattr(body,k) is None}))
    existing = db.scalar(select(Command).where(Command.idempotency_key == key))
    if existing:
        if existing.payload_hash != digest or existing.created_by != actor:
            raise DomainError("idempotency_conflict", "Idempotency key was already used for a different request", 409)
        return existing, False
    device = db.scalar(select(Device).where(Device.id == body.device_id).with_for_update().execution_options(populate_existing=True))
    if not device:
        raise DomainError("not_found", "Device not found", 404)
    # A concurrent identical request may have committed while this transaction waited
    # for the device sequence allocator lock. Re-read before any mutable safety check.
    existing = db.scalar(select(Command).where(Command.idempotency_key == key))
    if existing:
        if existing.payload_hash != digest or existing.created_by != actor:
            raise DomainError("idempotency_conflict", "Idempotency key was already used for a different request", 409)
        return existing, False
    now = now or utcnow()
    from .channel_control import target_channel, latest_channel, register_hold
    channel = target_channel(db, device, body.channel_id)
    is_switch = device.kind in {"switch", "light"}
    reason = eligibility(db, device, now, body.action, settings=settings, channel_id=body.channel_id)
    if reason:
        raise DomainError(reason, f"Command rejected by safety constraint: {reason}", 409)
    if device.source_mode == "REAL":
        from .models import CommissioningRecord
        release = db.get(CommissioningRecord, device.physical_release_id)
        confirmation = body.physical_confirmation
        if not confirmation or not confirmation.understands_mains_consequence or confirmation.device_id != device.id or confirmation.action != body.action or not release or confirmation.load_id != release.load_id:
            raise DomainError("physical_confirmation_required", "Explicitly confirm this device, its currently released named load, action and mains-power consequence", 409)
        if confirmation.release_id != release.id or confirmation.profile_revision != device.profile_revision:
            raise DomainError("physical_review_stale", "The reviewed release or device profile changed; fetch fresh eligibility and review the named load again", 409)
        if body.simulation_scenario != "success":
            raise DomainError("simulation_scenario_forbidden", "Fault injection scenarios cannot be applied to REAL commands", 422)
    active_query = select(Command).where(Command.device_id == device.id, Command.status.not_in(TERMINAL))
    if is_switch and device.provenance.get("command_concurrency", "per_channel") == "per_channel":
        active_query = active_query.where(Command.channel_id == channel.id)
    active = db.scalar(active_query.limit(1))
    if active:
        raise DomainError("command_in_flight", "Wait for the outstanding command to reach a terminal state", 409)
    if device.next_command_sequence > 2**64 - 1:
        raise DomainError("sequence_exhausted", "Device command sequence is exhausted; commissioning review required", 409)
    latest = latest_channel(db, channel) if is_switch else db.get(Telemetry, device.latest_telemetry_id)
    desired = (latest.value.get("actuator_reported_on") if is_switch else latest.desired_on) if body.action == "hold" else body.action == "restore"
    if desired is None:
        raise DomainError("unknown_requested_state", "Hold requires a known requested output state", 409)
    request_evidence={"source_mode":device.source_mode,"profile_revision":device.profile_revision,"desired_on":desired,
        "channel_id":channel.id if channel else None,"channel_key":channel.channel_key if channel else "relay.1",
        "verification_kind":"actuator_reported_only" if is_switch else "independent_feedback",
        "manual_hold_scope":"backend_edge" if body.manual_hold_seconds else None}
    if device.source_mode=="REAL":
        request_evidence.update(release_id=release.id,load_id=release.load_id,load_name=release.load_name,physical_review_confirmed=True)
    command = Command(id=uid("cmd"), channel_id=channel.id if channel else None, channel_key=channel.channel_key if channel else "relay.1",
        product_family="SWITCH" if is_switch else "PLUG", manual_hold_seconds=body.manual_hold_seconds, device_id=device.id, campus_id=device.campus_id, building_id=device.building_id, dispatch_mode=device.dispatch_mode,
        expected_boot_epoch=latest.boot_epoch, action=body.action, sequence=device.next_command_sequence,
        status="requested", reason=body.reason, source_mode=device.source_mode, issued_at=now, expires_at=now+timedelta(seconds=body.expires_in_seconds),
        created_by=actor, idempotency_key=key, payload_hash=digest, simulation_scenario=body.simulation_scenario, profile_revision=device.profile_revision,
        history=[{"status": "requested", "at": iso(now), "reason": body.reason, "evidence": request_evidence}], updated_at=now)
    device.next_command_sequence += 1
    db.add(command)
    db.flush()
    register_hold(db, command, device, channel, body.manual_hold_seconds, actor, now)
    audit(db, actor, "requested", "command", command.id, {"device_id": device.id, "action": body.action, "simulated": device.source_mode == "SIMULATED", "source_mode": device.source_mode})
    db.flush()
    return command, True


def advance_commands(db, now=None, settings=None):
    from .simulation import dispatch_simulated, accept_simulated, observe_simulated
    explicit_now = now
    # Session creation is lazy. Acquiring the connection starts the transaction and
    # waits for SQLite's BEGIN IMMEDIATE before reading the processing clock. A
    # pre-lock timestamp can otherwise reject newly committed evidence as future
    # data and write command history earlier than issued_at. Explicit test clocks
    # remain deterministic; production callers must leave now unset.
    db.connection()
    now = now or utcnow()
    batch_size = settings.control_batch_size if settings else 32
    expired = list(db.scalars(select(Command).where(Command.status.not_in(TERMINAL), Command.expires_at <= now).order_by(Command.expires_at, Command.id).with_for_update(skip_locked=True).limit(64)))
    urgency = case((Command.status == "acknowledged", 0), (Command.status == "dispatched", 1), else_=2)
    active = list(db.scalars(select(Command).where(Command.status.not_in(TERMINAL), Command.expires_at > now, Command.dispatch_mode == "IN_PROCESS",
        or_(Command.status != "acknowledged", Command.simulation_scenario != "timeout")).order_by(urgency, Command.expires_at, Command.id).with_for_update(skip_locked=True).limit(batch_size)))
    commands = expired + active
    for command in commands:
        device = db.get(Device, command.device_id)
        if explicit_now is None:
            # An earlier command or database query can consume this batch's time
            # budget. Recheck expiry and evidence with the current processing time.
            now = utcnow()
        if now >= command.expires_at:
            transition(db, command, "timed_out", "Command expired without verified evidence; actual state may be unknown", now=now)
            continue
        if command.profile_revision != device.profile_revision:
            transition(db, command, "rejected" if command.status in {"requested", "dispatched"} else "failed", "Device binding/profile changed after request", now=now)
            continue
        if command.dispatch_mode != "IN_PROCESS":
            # MQTT transport is driven by the authenticated adapter poll/receipt/ACK
            # boundary, never by a process-local success assumption.
            continue
        if command.source_mode != "SIMULATED" or device.source_mode != "SIMULATED":
            transition(db, command, "rejected" if command.status == "requested" else "failed", "In-process adapter only accepts simulated devices", now=now)
            continue
        if command.status == "requested":
            actor = db.get(User, command.created_by)
            if not actor or not actor.enabled or actor.role not in {"admin", "operator"} or (actor.campus_ids is not None and command.campus_id not in actor.campus_ids):
                transition(db, command, "rejected", "Issuing actor authorization was revoked before dispatch", now=now)
                continue
            from .room_control import policy_command_block
            blocked = eligibility(db, device, now, command.action, channel_id=command.channel_id) or policy_command_block(db, command, now)
            if blocked or command.simulation_scenario == "reject":
                transition(db, command, "rejected", blocked or "Injected simulated adapter rejection", now=now)
            else:
                if command.product_family == "SWITCH":
                    from .switch_simulation import dispatch_switch
                    dispatch_switch(db, command, device, now)
                else:
                    dispatch_simulated(db, command, device, now)
                transition(db, command, "dispatched", "Persisted request in the simulation output adapter", now=now)
        elif command.status == "dispatched":
            try:
                if command.product_family == "SWITCH":
                    from .switch_simulation import observe_switch
                    observe_switch(db, command, device, now)
                else:
                    accept_simulated(db, command, device, now)
            except DomainError as exc:
                transition(db, command, "failed", f"Simulation feedback contract rejected: {exc.code}", now=now)
        elif command.status == "acknowledged":
            try:
                observe_simulated(db, command, device, now)
            except DomainError as exc:
                transition(db, command, "failed", f"Simulation feedback contract rejected: {exc.code}", now=now)
    return len(commands)


def evaluate_strategy(db, strategy, actor, now=None):
    now = now or utcnow()
    query = select(Device).where(Device.campus_id == strategy.campus_id)
    if strategy.building_id:
        query = query.where(Device.building_id == strategy.building_id)
    devices = list(db.scalars(query).all())
    from .accounting import selected_devices
    baseline_devices = {d.id:d for d in selected_devices(db, strategy.campus_id, strategy.building_id, start=now, end=now) if d.source_mode == "SIMULATED"}
    baseline_ids=set(baseline_devices)
    candidates, rejected, baseline = [], [], 0.0
    observed_baseline = 0
    for device in devices:
        latest = db.get(Telemetry, device.latest_telemetry_id) if device.latest_telemetry_id else None
        if (device.id in baseline_ids and latest and latest.quality == "good" and latest.active_power_w is not None
                and latest.binding_id in baseline_devices[device.id].eligible_binding_ids
                and latest.campus_id==device.campus_id and latest.building_id==device.building_id
                and latest.circuit_id==device.circuit_id and latest.source_mode==device.source_mode
                and -5 <= (now-latest.observed_at).total_seconds() <= 120):
            baseline += max(0, latest.active_power_w) / 1000
            observed_baseline += 1
        if device.kind != "smart_plug":
            continue
        reason = eligibility(db, device, now)
        if reason:
            rejected.append({"device_id": device.id, "reason": reason})
        elif latest and latest.active_power_w and latest.active_power_w > 0:
            candidates.append((device, latest.active_power_w / 1000))
    candidates.sort(key=lambda x: (-x[1], x[0].id))
    chosen, reduction = [], 0.0
    target = baseline * strategy.target_reduction_pct / 100
    for device, kw in candidates:
        if len(chosen) >= strategy.max_devices or reduction >= target:
            break
        chosen.append(device.id)
        reduction += kw
    result = {"id": uid("eval"), "strategy_id": strategy.id, "created_at": iso(now), "mode": "SHADOW", "candidate_device_ids": chosen,
        "rejected_devices": rejected, "estimated_reduction_kw": round(reduction, 4), "baseline_kw": round(baseline, 4) if observed_baseline else None,
        "baseline_meter_count": observed_baseline, "expected_baseline_meter_count": len(baseline_ids),
        "baseline_coverage_ratio": observed_baseline/len(baseline_ids) if baseline_ids else None,
        "quality": "simulation_estimate" if observed_baseline == len(baseline_ids) and observed_baseline else "partial_simulation_estimate" if observed_baseline else "insufficient_data", "source_mode": "SIMULATED", "dispatch_performed": False,
        "target_reduction_pct": strategy.target_reduction_pct, "target_met": bool(observed_baseline) and observed_baseline == len(baseline_ids) and reduction >= target,
        "warning": "Load-shedding estimate is not measured energy savings or verified carbon reduction"}
    strategy.latest_evaluation = result
    strategy.status = "evaluated"
    strategy.approved_at = strategy.approved_by = None
    db.add(Evaluation(id=result["id"], strategy_id=strategy.id, created_at=now, content=result))
    audit(db, actor, "evaluated", "strategy", strategy.id, {"evaluation_id": result["id"], "dispatch_performed": False})
    return result
