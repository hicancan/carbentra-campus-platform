import hashlib
import json
from datetime import datetime
from uuid import uuid4
from sqlalchemy import inspect, select
from .db import iso
from .models import Audit, Event


class DomainError(Exception):
    def __init__(self, code, message, status=400, details=None):
        self.code, self.message, self.status, self.details = code, message, status, details
        super().__init__(message)


def uid(prefix):
    return f"{prefix}_{uuid4().hex}"


def payload_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def record_dict(obj, exclude=()):
    return {column.key: iso(value) if isinstance(value, datetime) else value
            for column in inspect(obj).mapper.column_attrs
            if column.key not in exclude
            for value in [getattr(obj, column.key)]}


def audit(db, actor, action, entity_type, entity_id, details=None):
    from .models import Device, Command, Alarm, Strategy, Report, Circuit, ScheduleEvent, CommissioningRecord
    model = {"device": Device, "command": Command, "alarm": Alarm, "strategy": Strategy, "report": Report, "circuit": Circuit, "schedule": ScheduleEvent, "commissioning": CommissioningRecord}.get(entity_type)
    row = db.get(model, entity_id) if model else None
    if row is None and model:
        row = next((x for x in db.new if isinstance(x, model) and x.id == entity_id), None)
    campus_id = getattr(row, "campus_id", None)
    db.add(Audit(actor=actor, action=action, entity_type=entity_type, entity_id=str(entity_id), details=details or {}, campus_id=campus_id))
    db.add(Event(type=f"{entity_type}.{action}", entity_id=str(entity_id), campus_id=campus_id))


def require_entity(db, model, entity_id):
    row = db.get(model, entity_id)
    if row is None:
        raise DomainError("not_found", f"{model.__name__} not found", 404)
    return row


def locked_entity(db, model, entity_id):
    db.flush()
    row = db.scalar(select(model).where(model.id == entity_id).with_for_update().execution_options(populate_existing=True))
    if row is None:
        raise DomainError("not_found", f"{model.__name__} not found", 404)
    return row


def envelope(data, **meta):
    result = {"data": data}
    if meta:
        result["meta"] = meta
    return result
