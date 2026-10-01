"""Per-channel actuator-reported control, distinct from independently sensed Plug feedback."""
from datetime import timedelta
from sqlalchemy import select
from .common import DomainError, require_entity, uid
from .db import utcnow
from .models import DeviceChannel, ChannelObservation, ChannelHold, HardwareEvent, Binding, Command


def target_channel(db, device, channel_id=None):
    if channel_id:
        channel = require_entity(db, DeviceChannel, channel_id)
        if channel.device_id != device.id:
            raise DomainError("channel_device_mismatch", "Channel is not owned by the requested device", 409)
        return channel
    if device.kind in {"switch", "light"}:
        raise DomainError("channel_required", "Select the exact Switch relay channel", 422)
    return db.scalar(select(DeviceChannel).where(DeviceChannel.device_id == device.id, DeviceChannel.channel_key == "relay.1"))


def latest_channel(db, channel):
    return db.scalar(select(ChannelObservation).where(ChannelObservation.channel_id == channel.id).order_by(
        ChannelObservation.observed_at.desc(), ChannelObservation.id.desc()).limit(1))


def channel_hold_until(db, channel_id, now=None):
    now = now or utcnow()
    row = db.scalar(select(ChannelHold).where(ChannelHold.channel_id == channel_id, ChannelHold.starts_at <= now,
        ChannelHold.ends_at > now).order_by(ChannelHold.ends_at.desc()).limit(1))
    return row.ends_at if row else None


def switch_gate(db, device, channel, now, ignore_dwell=False):
    if device.source_mode != "SIMULATED":
        return "physical_control_disabled"
    if not channel or channel.channel_key not in {"relay.1", "relay.2", "relay.3"} or "relay.commanded" not in channel.capabilities:
        return "unsupported_channel_capability"
    if not channel.controllable:
        return "control_not_authorized"
    row = latest_channel(db, channel)
    max_age = 10 if device.dispatch_mode == "VIRTUAL" else 120
    received_simulation = bool(row and device.source_mode == "SIMULATED" and row.quality == "uncertain" and set(row.quality_flags) == {"TIME_UNCERTAIN"})
    basis_time = row.received_at if received_simulation else row.observed_at if row else now
    if not row or (row.quality != "good" and not received_simulation) or not -5 <= (now-basis_time).total_seconds() <= max_age:
        return "stale_or_invalid_actuator_report"
    if type(row.value.get("actuator_reported_on")) is not bool:
        return "unknown_actuator_report"
    binding = db.scalar(select(Binding).where(Binding.device_id == device.id, Binding.valid_to.is_(None)).limit(1))
    if not binding or row.binding_id != binding.id or any(getattr(device,k) != getattr(binding,k) for k in ("campus_id","building_id","space_id","floor_id","circuit_id")):
        return "observation_binding_mismatch"
    if row.value.get("fault_latched") is not False:
        return "local_fault_or_unknown_health"
    event = db.get(HardwareEvent, row.event_id) if row.event_id else None
    if event:
        raw = event.raw_payload.get("raw", {})
        if raw.get("maintenance") or raw.get("fault_latched"):
            return "local_safety_interlock"
        if raw.get("actuation_enabled") is not True:
            return "actuation_not_enabled"
        number = int(channel.channel_key.rsplit('.',1)[1])
        if int(raw.get("protected_channel_mask", 0)) & (1 << (number-1)):
            return "protected_channel"
        local = next((x for x in raw.get("channels", []) if x.get("channel") == number), {})
        if local.get("control_mode") in {"maintenance", "protected"}:
            return "local_channel_interlock"
        if local.get("control_mode") == "manual":
            return "local_manual_hold"
    if not ignore_dwell and channel.last_control_at and (now-channel.last_control_at).total_seconds() < device.minimum_dwell_seconds:
        return "minimum_dwell"
    return None


def register_hold(db, command, device, channel, seconds, actor, now):
    if not seconds:
        return
    if not channel:
        # Legacy Plug callers acquire an explicit stable target only when they ask
        # for per-channel persistence; ordinary legacy command behavior is unchanged.
        channel = DeviceChannel(id=f"{device.id}:relay.1", device_id=device.id, campus_id=device.campus_id,
            channel_key="relay.1", name=f"{device.name} · relay.1", kind="socket", unit="W", freshness_seconds=120,
            capabilities=["relay.commanded","relay.feedback","power.active"], controllable=True)
        db.add(channel);db.flush()
        command.channel_id = channel.id
    db.add(ChannelHold(id=uid("channel_hold"), channel_id=channel.id, device_id=device.id, campus_id=device.campus_id,
        command_id=command.id, starts_at=now, ends_at=now+timedelta(seconds=seconds), created_by=actor, reason=command.reason))
