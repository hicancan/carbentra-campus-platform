"""Operator-attested evidence workflow, never an automatic hardware safety certification.
Activation needs an independent deployment allowlist and all normal runtime guards.
"""
from datetime import timedelta
from sqlalchemy import select
from .models import CommissioningRecord, Binding, Telemetry
from .common import DomainError, audit
from .db import utcnow


def create_record(db, device, body, actor):
    now = utcnow()
    if device.source_mode != "REAL":
        raise DomainError("physical_device_required", "Commissioning records are for explicitly registered REAL devices", 409)
    if db.get(CommissioningRecord, body.id):
        raise DomainError("immutable_release", "Commissioning release IDs are immutable", 409)
    if not now < body.valid_until <= now+timedelta(days=365):
        raise DomainError("invalid_release_window", "Release must expire within one year", 422)
    binding = db.scalar(select(Binding).where(Binding.device_id == device.id, Binding.valid_to.is_(None)).limit(1))
    if not binding:
        raise DomainError("binding_required", "A dated placement is required before commissioning", 409)
    row = CommissioningRecord(**body.model_dump(), device_id=device.id, campus_id=device.campus_id, binding_id=binding.id, created_by=actor)
    db.add(row)
    audit(db, actor, "recorded", "commissioning", row.id, {"device_id": device.id, "status": "pending", "automatic_safety_certification": False})
    return row


def release_device(db, device, body, settings, actor):
    now = utcnow()
    if not settings.physical_dispatch_enabled or body.release_id not in settings.physical_release_ids:
        raise DomainError("physical_control_disabled", "Independent deployment release gate is closed", 409)
    release = db.get(CommissioningRecord, body.release_id)
    if not release or release.device_id != device.id:
        raise DomainError("not_found", "Commissioning record not found", 404)
    if not release.load_id or not release.load_name:
        raise DomainError("load_binding_required", "A specific named load binding is required in the immutable commissioning record", 409)
    if release.status == "revoked" or release.valid_until <= now:
        raise DomainError("release_inactive", "Release is revoked or expired", 409)
    if not body.operator_attested or not body.noncritical_load_attested:
        raise DomainError("attestation_required", "An authorized operator must explicitly attest reviewed safety evidence and noncritical load approval", 409)
    binding = db.scalar(select(Binding).where(Binding.device_id == device.id, Binding.valid_to.is_(None)).limit(1))
    if not binding or release.binding_id != binding.id:
        raise DomainError("binding_changed", "Placement changed after the evidence record; a new commissioning record is required", 409)
    latest = db.get(Telemetry, device.latest_telemetry_id) if device.latest_telemetry_id else None
    age = (now-latest.observed_at).total_seconds() if latest else None
    if device.source_mode != "REAL" or device.kind != "smart_plug" or not latest or latest.source_mode != "REAL" or latest.binding_id != release.binding_id or latest.quality != "good" or latest.time_source != "authenticated" or latest.fault_latched or age < 0 or age > 10:
        raise DomainError("commissioning_observation_invalid", "Release requires a fresh authenticated valid physical-device observation without a latched fault", 409)
    if latest.raw_payload.get("board_revision") != release.hardware_revision:
        raise DomainError("hardware_revision_mismatch", "Observed hardware revision does not match commissioning evidence", 409)
    if not {"shed", "restore", "hold"}.issubset(set(device.capabilities)):
        raise DomainError("unsupported_capability", "Registered device lacks the required control capabilities", 409)
    device.commissioned, device.allow_control, device.critical = True, True, False
    device.dispatch_mode, device.physical_release_id = "PHYSICAL", release.id
    device.profile_id = release.profile_id
    device.provenance = {**device.provenance, "load_binding": {"id": release.load_id, "name": release.load_name, "profile_id": release.profile_id, "commissioning_id": release.id, "basis": "operator_attestation"}}
    device.profile_revision += 1
    release.status, release.released_at, release.released_by = "released", now, actor
    audit(db, actor, "released", "commissioning", release.id, {"device_id": device.id, "operator_attested": True, "note": body.note, "automatic_safety_certification": False})
    return release


def revoke_release(db, device, release, actor, note):
    if release.device_id != device.id:
        raise DomainError("not_found", "Commissioning record not found", 404)
    release.status, release.revoked_at = "revoked", utcnow()
    if device.physical_release_id == release.id:
        device.commissioned = device.allow_control = False
        device.dispatch_mode = "DISABLED"
        device.profile_revision += 1
    audit(db, actor, "revoked", "commissioning", release.id, {"note": note, "in_flight_delivery_may_be_uncertain": True})
    return release
