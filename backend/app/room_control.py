"""Bounded room policies use the genuine device command ledger; evaluations are not outcomes."""
from datetime import timedelta
from sqlalchemy import select
from .models import DeviceChannel, Device, RoomPolicy, RoomEvaluation, Space, Command
from .common import DomainError, uid, require_entity, record_dict, locked_entity, payload_hash
from .db import utcnow
from .classrooms import snapshots, timeline, audit_room
from .schemas import CommandIn
from .control import eligibility, create_command, command_dict, TERMINAL


def create_policy(db, space, body, actor):
    for channel_id in body.channel_ids:
        channel = require_entity(db, DeviceChannel, channel_id)
        device = require_entity(db, Device, channel.device_id)
        if device.space_id != space.id:
            raise DomainError("policy_scope_mismatch", "Every target must be bound to this room", 409)
        if not channel.controllable or channel.kind not in {"socket", "lighting"}:
            raise DomainError("read_only_channel", "Policy targets require declared relay capability", 409)
        if body.mode == "SIMULATED" and device.source_mode != "SIMULATED":
            raise DomainError("physical_control_disabled", "Room scheduling can only dispatch simulated loads", 409)
    values = body.model_dump()
    config = {k: values.pop(k) for k in ("channel_ids", "action", "vacant_for_seconds", "minimum_power_w", "max_commands", "reason")}
    row = RoomPolicy(id=uid("policy"), space_id=space.id, campus_id=space.campus_id,
        created_by=actor, config=config, **values)
    db.add(row)
    audit_room(db, actor, "created", space, "room_policy", row.id, {"mode": row.mode, "actuation": "SIMULATED_ONLY"})
    db.flush()
    return row


def evaluate_policy(db, policy, actor, now=None, settings=None):
    now = now or utcnow()
    space = require_entity(db, Space, policy.space_id)
    state = snapshots(db, [space], now)[0]
    lookback = policy.config["vacant_for_seconds"]
    history = timeline(db, space, now-timedelta(seconds=lookback), now)
    vacancy = 0.
    for interval in reversed(history["intervals"]):
        if interval["occupancy"] != "vacant":
            break
        vacancy += interval["duration_seconds"]
    shared = []
    if not policy.enabled:
        shared.append("policy_disabled")
    if not policy.starts_at <= now < policy.ends_at:
        shared.append("outside_policy_window")
    if state["mode"] != "automatic":
        shared.append(f"room_{state['mode']}_mode")
    if state["occupancy"] != "vacant" or vacancy < lookback:
        shared.append("vacancy_not_persisted")
    states = {c["channel_id"]: c for c in state["channels"]}
    targets = []
    eligible_count = 0
    for channel_id in policy.config["channel_ids"]:
        channel = db.get(DeviceChannel, channel_id)
        current = states.get(channel_id)
        device = db.get(Device, channel.device_id) if channel else None
        blocked = list(shared)
        aggregate = None
        power = current["value"].get("active_power_w") if current and current["value"] else None
        if not channel or not current or not device or device.space_id != space.id:
            blocked.append("target_binding_changed")
        else:
            if not channel.controllable:
                blocked.append("read_only_channel")
            if device.source_mode != "SIMULATED":
                blocked.append("physical_control_disabled")
            gate = eligibility(db, device, now, "shed", settings=settings, channel_id=channel_id)
            if gate:
                blocked.append(gate)
            reported = current["value"].get("actuator_reported_on") if current["value"] and device.kind in {"switch", "light"} else current["value"].get("output_present") if current["value"] else None
            if current["quality"] != "good" or reported is not True:
                blocked.append("load_not_observed_on")
            aggregate = next((c["value"].get("active_power_w") for c in state["channels"] if c["device_id"] == device.id and c["kind"] == "power" and c["quality"] == "good" and c["value"]), None)
            threshold_power = power if power is not None else aggregate
            if threshold_power is None or threshold_power < policy.config["minimum_power_w"]:
                blocked.append("insufficient_known_power")
            from .channel_control import channel_hold_until
            if channel_hold_until(db, channel.id, now):
                blocked.append("channel_manual_hold")
            if db.scalar(select(Command.id).where(Command.device_id == device.id, Command.channel_id == channel.id if device.kind in {"switch", "light"} else True, Command.status.not_in(TERMINAL)).limit(1)):
                blocked.append("command_in_flight")
            if not blocked and eligible_count >= policy.config["max_commands"]:
                blocked.append("bounded_command_limit")
        if not blocked:
            eligible_count += 1
        targets.append({"channel_id": channel_id, "device_id": device.id if device else None,
            "eligible": not blocked, "blocked_by": sorted(set(blocked)), "observed_power_w": power, "aggregate_power_w": aggregate})
    powers = [t["observed_power_w"] for t in targets if t["eligible"]]
    content = {"occupancy": state["occupancy"], "vacancy_seconds": vacancy, "mode": state["mode"], "targets": targets,
        "eligible_count": eligible_count, "modeled_reduction_w": sum(powers) if powers and all(p is not None for p in powers) else None, "savings_claim": False,
        "source_mode": "SIMULATED" if all(c["source_mode"] == "SIMULATED" for c in state["channels"]) and state["channels"] else "MIXED" if state["channels"] else "UNKNOWN",
        "explanation": "Conditional modeled reduction from currently observed eligible load; no measured savings. Occupancy plans never authorize control. Every dispatch rechecks fresh state, dwell, binding, mode and authorization."}
    row = RoomEvaluation(id=uid("room_eval"), policy_id=policy.id, space_id=space.id, campus_id=space.campus_id,
        at=now, policy_revision=policy.revision, created_by=actor, content=content, command_ids=[])
    db.add(row)
    audit_room(db, actor, "evaluated", space, "room_policy", policy.id, {"evaluation_id": row.id, "eligible_count": eligible_count})
    db.flush()
    return row


def evaluation_dict(db, row):
    result = record_dict(row)
    commands = list(db.scalars(select(Command).where(Command.id.in_(row.command_ids)).order_by(Command.issued_at, Command.id)))
    result["commands"] = [command_dict(c) for c in commands]
    result["verified_count"] = sum(c.status == "verified" for c in commands)
    result["unverified_count"] = sum(c.status == "acknowledged_unverified" for c in commands)
    result["failed_count"] = sum(c.status in {"rejected", "failed", "timed_out"} for c in commands)
    result["pending_count"] = sum(c.status not in TERMINAL for c in commands)
    policy = db.get(RoomPolicy, row.policy_id)
    result["execution_status"] = ("shadow" if policy and policy.mode == "SHADOW" else "not_dispatched") if row.dispatched_at is None else (
        "pending" if result["pending_count"] else "verified" if commands and result["verified_count"] == len(commands) else
        "acknowledged_unverified" if commands and result["unverified_count"] == len(commands) else
        "partial" if result["verified_count"] or result["unverified_count"] else "failed")
    return result


def dispatch_evaluation(db, evaluation, actor, settings=None, now=None):
    now = now or utcnow()
    evaluation = locked_entity(db, RoomEvaluation, evaluation.id)
    if evaluation.dispatched_at:
        return evaluation
    policy = locked_entity(db, RoomPolicy, evaluation.policy_id)
    if policy.mode != "SIMULATED":
        raise DomainError("shadow_only", "SHADOW evaluations never dispatch commands", 409)
    if evaluation.policy_revision != policy.revision or not 0 <= (now-evaluation.at).total_seconds() <= 30:
        raise DomainError("evaluation_expired", "Evaluate again; review is older than 30 seconds or policy changed", 409)
    # Re-evaluate rather than trusting client-provided eligibility or old evidence.
    fresh = evaluate_policy(db, policy, actor, now, settings)
    originally_eligible = {t["channel_id"] for t in evaluation.content["targets"] if t["eligible"]}
    candidates = [t for t in fresh.content["targets"] if t["eligible"] and t["channel_id"] in originally_eligible]
    if not candidates:
        raise DomainError("no_eligible_targets", "Fresh evidence no longer permits a simulated command", 409)
    ids = []
    for target in candidates:
        body = CommandIn(device_id=target["device_id"], channel_id=target["channel_id"], action=policy.config["action"], reason=f"Room policy {policy.name}: {policy.config['reason']}", expires_in_seconds=30)
        command, _ = create_command(db, body, f"room-{evaluation.id}-{payload_hash(target['channel_id'])[:16]}", actor, now, settings)
        command.history = [{**command.history[0], "evidence": {**command.history[0]["evidence"], "room_policy_id": policy.id, "room_policy_revision": policy.revision, "room_evaluation_id": evaluation.id}}, *command.history[1:]]
        ids.append(command.id)
    evaluation.command_ids, evaluation.dispatched_at = ids, now
    audit_room(db, actor, "dispatched", require_entity(db, Space, policy.space_id), "room_evaluation", evaluation.id,
        {"command_ids": ids, "outcome": "requested_not_verified"})
    db.flush()
    return evaluation


def policy_command_block(db, command, now):
    """Queued automatic intent loses authority when occupancy/mode/lease changes."""
    evidence = command.history[0].get("evidence", {}) if command.history else {}
    policy_id = evidence.get("room_policy_id")
    if not policy_id:
        return None
    from .channel_control import channel_hold_until
    if command.channel_id and channel_hold_until(db, command.channel_id, now):
        return "channel_manual_hold"
    policy = db.get(RoomPolicy, policy_id)
    if not policy or not policy.enabled or policy.mode != "SIMULATED" or policy.revision != evidence.get("room_policy_revision"):
        return "room_policy_authority_revoked"
    if not policy.starts_at <= now < policy.ends_at:
        return "room_policy_window_expired"
    space = db.get(Space, policy.space_id)
    if not space:
        return "room_policy_scope_unavailable"
    state = snapshots(db, [space], now)[0]
    if state["mode"] != "automatic":
        return f"room_{state['mode']}_override"
    if state["occupancy"] != "vacant":
        return "vacancy_no_longer_observed"
    history = timeline(db, space, now-timedelta(seconds=policy.config["vacant_for_seconds"]), now)
    if any(s["occupancy"] != "vacant" for s in history["intervals"]):
        return "vacancy_not_persisted"
    if not any(c["device_id"] == command.device_id and c["channel_id"] in policy.config["channel_ids"] for c in state["channels"]):
        return "room_policy_binding_changed"
    return None
