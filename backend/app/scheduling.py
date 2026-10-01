"""Plans are not observations and can never independently authorize load control."""
from sqlalchemy import select
from .models import ScheduleEvent, Space, Building, Device
from .common import require_entity, DomainError, uid, audit, record_dict
from .registry import validate_binding
from .db import utcnow


def schedule_dict(row):
    return {**record_dict(row), "observed_occupancy": "unknown", "control_authorization": False}


def validate_schedule(db, values):
    validate_binding(db, {"campus_id": values["campus_id"], "building_id": values.get("building_id")})
    if values.get("space_id"):
        space = require_entity(db, Space, values["space_id"])
        if space.campus_id != values["campus_id"] or space.building_id != values.get("building_id"):
            raise DomainError("binding_mismatch", "Scheduled space is outside the selected campus/building", 409)


def create_schedule(db, values, actor):
    validate_schedule(db, values)
    row = ScheduleEvent(id=uid("schedule"), **values, created_by=actor)
    db.add(row)
    audit(db, actor, "created", "schedule", row.id, {"planned_only": True, "source_mode": row.source_mode})
    db.flush()
    return row


def control_block(db, device, now):
    # Active maintenance is a conservative interlock. Absence of a scheduled class,
    # a holiday, or planned occupancy=0 is never evidence that a room is empty/safe.
    query = select(ScheduleEvent).where(ScheduleEvent.campus_id == device.campus_id, ScheduleEvent.status == "scheduled",
        ScheduleEvent.kind == "maintenance", ScheduleEvent.starts_at <= now, ScheduleEvent.ends_at > now)
    for row in db.scalars(query):
        if row.building_id and row.building_id != device.building_id:
            continue
        if row.space_id and row.space_id != device.space_id:
            continue
        return "maintenance_interlock"
    return None
