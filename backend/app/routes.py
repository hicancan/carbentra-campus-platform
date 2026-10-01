import asyncio
import csv
import io
import json
from datetime import datetime, timedelta
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from . import __version__
from .common import DomainError, envelope, record_dict, require_entity, locked_entity, audit, uid
from .db import utcnow, iso
from .models import Campus, Building, Floor, Space, Circuit, Device, Binding, Telemetry, Command, Alarm, CarbonFactor, Tariff, Strategy, Report, Audit, Event, State, Session
from .schemas import LoginIn, DeviceIn, DevicePatch, BindingIn, CircuitIn, IngestIn, CommandIn, NoteIn, RequiredNote, FactorIn, TariffIn, StrategyIn, ReportIn, SettingsPatch
from .security import get_db, current_user, roles, login, auth_payload, adapter_auth, client_address, global_admin, COOKIE
from .registry import validate_binding, create_device, add_binding, device_dict, device_list, telemetry_dict, freshness_limits
from .telemetry import ingest_batch, normalize_firmware, ingest_sample
from .accounting import compute_energy, apply_accounting, breakdown, balance, period
from .analytics import overview
from .control import create_command, command_dict, evaluate_strategy

from .responses import (Envelope, ErrorEnvelope, AuthResponse, LogoutResponse, DeviceResponse, DeviceDetailResponse,
    TelemetryResponse, CommandResponse, EnergySummaryResponse, EnergyBreakdownResponse, EnergyBalanceResponse,
    FactorResponse, TariffResponse, CarbonSummaryResponse, CostSummaryResponse, ForecastResponse, ControlEligibilityResponse)

router = APIRouter(prefix="/api/v1", responses={code: {"model": ErrorEnvelope} for code in (400,401,403,404,409,413,422,429,500,503)})
Read = Annotated[object, Depends(current_user)]
Operate = Annotated[object, Depends(roles("admin", "operator"))]
Analyze = Annotated[object, Depends(roles("admin", "analyst"))]
Admin = Annotated[object, Depends(roles("admin"))]
GlobalAdmin = Annotated[object, Depends(global_admin)]
DB = Annotated[object, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=500)]
Offset = Annotated[int, Query(ge=0)]


def paginated(db, query, limit, offset, serialize=record_dict):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.scalars(query.limit(limit).offset(offset)).all()
    return envelope([serialize(x) for x in rows], total=total, limit=limit, offset=offset)


def scope_dict(campus_id, building_id, start, end, device_ids=None):
    result = {"campus_id": campus_id, "building_id": building_id, "start": start, "end": end}
    if device_ids:
        result["device_ids"] = device_ids.split(",")
    return result


@router.post("/auth/login", response_model=Envelope[AuthResponse], response_model_exclude_unset=True, tags=["auth"])
def auth_login(body: LoginIn, request: Request, response: Response, db: DB):
    settings = request.app.state.settings
    token, user, session = login(db, settings, body, client_address(request))
    response.set_cookie(COOKIE, token, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_hours*3600, path="/")
    return envelope(auth_payload(user, session))


@router.get("/auth/me", response_model=Envelope[AuthResponse], response_model_exclude_unset=True, tags=["auth"])
def auth_me(request: Request, user: Read):
    return envelope(auth_payload(user, request.state.auth_session))


@router.post("/auth/logout", response_model=Envelope[LogoutResponse], response_model_exclude_unset=True, tags=["auth"])
def auth_logout(request: Request, response: Response, db: DB, user: Read):
    db.delete(request.state.auth_session)
    audit(db, user.id, "logout", "session", user.id)
    db.commit()
    response.delete_cookie(COOKIE, path="/", secure=request.app.state.settings.cookie_secure, httponly=True, samesite="lax")
    return envelope({"logged_out": True})


@router.get("/campuses", tags=["registry"])
def campuses(db: DB, user: Read, limit: Limit=100, offset: Offset=0):
    return paginated(db, select(Campus).order_by(Campus.name), limit, offset)


@router.get("/buildings", tags=["registry"])
def buildings(db: DB, user: Read, campus_id: str | None=None, q: str | None=None, limit: Limit=200, offset: Offset=0):
    query = select(Building)
    if campus_id:
        query = query.where(Building.campus_id == campus_id)
    if q:
        query = query.where(Building.name.ilike(f"%{q[:200]}%"))
    counts = dict(db.execute(select(Device.building_id, func.count()).group_by(Device.building_id)).all())
    return paginated(db, query.order_by(Building.name), limit, offset, lambda b: {**record_dict(b), "device_count": counts.get(b.id, 0)})


@router.get("/buildings/{building_id}", tags=["registry"])
def building_detail(building_id: str, db: DB, user: Read):
    building = require_entity(db, Building, building_id)
    return envelope({**record_dict(building), "device_count": db.scalar(select(func.count()).select_from(Device).where(Device.building_id == building_id))})


@router.get("/floors", tags=["registry"])
def floors(db: DB, user: Read, building_id: str | None=None, limit: Limit=200, offset: Offset=0):
    query = select(Floor)
    if building_id:
        query = query.where(Floor.building_id == building_id)
    return paginated(db, query.order_by(Floor.building_id, Floor.level), limit, offset)


@router.get("/spaces", tags=["registry"])
def spaces(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, floor_id: str | None=None, q: str | None=None, limit: Limit=100, offset: Offset=0):
    query = select(Space)
    for key, value in {"campus_id": campus_id, "building_id": building_id, "floor_id": floor_id}.items():
        if value:
            query = query.where(getattr(Space, key) == value)
    if q:
        query = query.where(Space.name.ilike(f"%{q[:200]}%"))
    return paginated(db, query.order_by(Space.name), limit, offset)


@router.get("/topology", tags=["registry"])
def topology(request: Request, db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None):
    cq, dq = select(Circuit), select(Device)
    for key, value in {"campus_id": campus_id, "building_id": building_id}.items():
        if value:
            cq, dq = cq.where(getattr(Circuit, key) == value), dq.where(getattr(Device, key) == value)
    return envelope({"circuits": [record_dict(c) for c in db.scalars(cq)], "devices": device_list(db, list(db.scalars(dq)), request.app.state.settings)})


@router.post("/circuits", status_code=201, tags=["registry"])
def circuit_create(body: CircuitIn, db: DB, user: Operate):
    if db.get(Circuit, body.id):
        raise DomainError("already_exists", "Circuit identity already exists", 409)
    validate_binding(db, {"campus_id": body.campus_id, "building_id": body.building_id})
    if body.space_id:
        space = require_entity(db, Space, body.space_id)
        if space.building_id != body.building_id:
            raise DomainError("binding_mismatch", "Space belongs to another building", 409)
    if body.parent_id:
        parent = require_entity(db, Circuit, body.parent_id)
        if parent.campus_id != body.campus_id or parent.building_id != body.building_id or parent.source_mode != body.source_mode:
            raise DomainError("topology_mismatch", "Parent must share campus, building and source mode", 409)
    row = Circuit(**body.model_dump())
    db.add(row)
    audit(db, user.id, "created", "circuit", row.id)
    db.commit()
    return envelope(record_dict(row))


@router.get("/assets/manifest", tags=["registry"])
def assets_manifest(request: Request, db: DB, user: Read):
    path = request.app.state.settings.spatial_manifest_path
    if not path.is_file():
        raise DomainError("spatial_unavailable", "Pinned spatial manifest is not installed", 503)
    return envelope({**json.loads(path.read_text(encoding="utf-8")), "base_url": "/assets/spatial", "availability": "reference_only", "runtime_state_source": "authenticated_api"})


@router.get("/devices", response_model=Envelope[list[DeviceResponse]], response_model_exclude_unset=True, tags=["devices"])
def devices(request: Request, db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, space_id: str | None=None, q: str | None=None,
            status: Literal["online", "stale", "offline", "unknown"] | None=None, source_mode: Literal["SIMULATED", "REAL", "REPLAYED"] | None=None, limit: Limit=100, offset: Offset=0):
    query = select(Device)
    for key, value in {"campus_id": campus_id, "building_id": building_id, "space_id": space_id, "source_mode": source_mode}.items():
        if value:
            query = query.where(getattr(Device, key) == value)
    if q:
        query = query.where(or_(Device.name.ilike(f"%{q[:200]}%"), Device.id.ilike(f"%{q[:200]}%")))
    if status:
        now, (stale, offline) = utcnow(), freshness_limits(db, request.app.state.settings)
        conditions = {"unknown": Device.last_seen_at.is_(None), "online": Device.last_seen_at >= now-timedelta(seconds=stale),
            "stale": (Device.last_seen_at < now-timedelta(seconds=stale)) & (Device.last_seen_at >= now-timedelta(seconds=offline)), "offline": Device.last_seen_at < now-timedelta(seconds=offline)}
        query = query.where(conditions[status])
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = list(db.scalars(query.order_by(Device.name, Device.id).limit(limit).offset(offset)))
    return envelope(device_list(db, rows, request.app.state.settings), total=total, limit=limit, offset=offset)


@router.post("/devices", response_model=Envelope[DeviceResponse], response_model_exclude_unset=True, status_code=201, tags=["devices"])
def device_create(body: DeviceIn, request: Request, db: DB, user: Operate):
    device = create_device(db, body.model_dump(), user.id)
    db.commit()
    return envelope(device_dict(db, device, request.app.state.settings))


@router.get("/devices/{device_id}", response_model=Envelope[DeviceDetailResponse], response_model_exclude_unset=True, tags=["devices"])
def device_detail(device_id: str, request: Request, db: DB, user: Read):
    device = require_entity(db, Device, device_id)
    result = device_dict(db, device, request.app.state.settings, limits=freshness_limits(db, request.app.state.settings))
    result["binding_history"] = [record_dict(x) for x in db.scalars(select(Binding).where(Binding.device_id == device_id).order_by(Binding.valid_from.desc()))]
    result["command_count"] = db.scalar(select(func.count()).select_from(Command).where(Command.device_id == device_id))
    return envelope(result)


@router.patch("/devices/{device_id}", response_model=Envelope[DeviceResponse], response_model_exclude_unset=True, tags=["devices"])
def device_update(device_id: str, body: DevicePatch, request: Request, db: DB, user: Operate):
    device = locked_entity(db, Device, device_id)
    changes = body.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise DomainError("invalid_patch", "Explicit null is not accepted for these fields", 422)
    effective = {"critical": device.critical, "allow_control": device.allow_control, **changes}
    if changes.get("dispatch_mode") == "VIRTUAL":
        import re
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,47}", device.id) or not re.fullmatch(r"[A-Za-z0-9_-]{1,47}", device.profile_id):
            raise DomainError("wire_identity_unsupported", "Virtual transport requires canonical 1–47 character device/profile identifiers", 409)
    if device.source_mode != "SIMULATED" and (changes.get("commissioned") or effective["allow_control"] or changes.get("dispatch_mode") in {"VIRTUAL", "IN_PROCESS"}):
        raise DomainError("physical_control_disabled", "Physical commissioning requires a separate verified release process", 409)
    if effective["critical"] and effective["allow_control"]:
        raise DomainError("critical_load", "Critical loads cannot be control-enabled", 409)
    for key, value in changes.items():
        setattr(device, key, value)
    if any(key in changes for key in ("critical", "allow_control", "commissioned", "dispatch_mode")):
        device.profile_revision += 1
    audit(db, user.id, "updated", "device", device_id, changes)
    db.commit()
    return envelope(device_dict(db, device, request.app.state.settings))


@router.put("/devices/{device_id}/binding", response_model=Envelope[DeviceResponse], response_model_exclude_unset=True, tags=["devices"])
def device_binding(device_id: str, body: BindingIn, request: Request, db: DB, user: Operate):
    device = locked_entity(db, Device, device_id)
    values = body.model_dump(exclude={"reason"})
    validate_binding(db, values)
    if all(getattr(device, key) == value for key, value in values.items()):
        return envelope(device_dict(db, device, request.app.state.settings))
    if device.kind == "meter":
        raise DomainError("meter_binding_change_requires_topology", "Meter relocation requires a new measurement boundary; register a replacement meter instead", 409)
    for key, value in values.items():
        setattr(device, key, value)
    device.commissioned = device.allow_control = False
    device.profile_revision += 1
    add_binding(db, device, user.id, body.reason)
    audit(db, user.id, "rebound", "device", device.id, {**values, "reason": body.reason, "commissioning_reset": True})
    db.commit()
    return envelope(device_dict(db, device, request.app.state.settings))


@router.get("/telemetry", response_model=Envelope[list[TelemetryResponse]], response_model_exclude_unset=True, tags=["telemetry"])
def telemetry(db: DB, user: Read, device_id: str | None=None, campus_id: str | None=None, building_id: str | None=None, circuit_id: str | None=None, start: datetime | None=None, end: datetime | None=None, limit: Limit=200, offset: Offset=0):
    start, end = period(start, end)
    query = select(Telemetry).where(Telemetry.observed_at >= start, Telemetry.observed_at <= end)
    for key, value in {"device_id": device_id, "campus_id": campus_id, "building_id": building_id, "circuit_id": circuit_id}.items():
        if value:
            query = query.where(getattr(Telemetry, key) == value)
    return paginated(db, query.order_by(Telemetry.observed_at.desc(), Telemetry.id.desc()), limit, offset, telemetry_dict)


@router.get("/devices/{device_id}/telemetry", response_model=Envelope[list[TelemetryResponse]], response_model_exclude_unset=True, tags=["telemetry"])
def device_telemetry(device_id: str, db: DB, user: Read, start: datetime | None=None, end: datetime | None=None, limit: Limit=200, offset: Offset=0):
    require_entity(db, Device, device_id)
    return telemetry(db, user, device_id=device_id, start=start, end=end, limit=limit, offset=offset)


@router.post("/ingest/telemetry", tags=["ingestion"])
def ingest(body: IngestIn, request: Request, db: DB, adapter=Depends(adapter_auth)):
    allowed = request.app.state.settings.adapter_allowed_device_ids
    if not allowed:
        raise DomainError("adapter_scope_unconfigured", "Configure an explicit adapter device allowlist", 503)
    return envelope(ingest_batch(db, body.samples, allowed))


@router.post("/ingest/firmware", tags=["ingestion"])
def ingest_firmware(body: dict, request: Request, db: DB, adapter=Depends(adapter_auth)):
    if body.get("device_id") not in request.app.state.settings.adapter_allowed_device_ids:
        raise DomainError("adapter_scope_denied", "Adapter is not authorized for this identity", 403)
    device = require_entity(db, Device, body.get("device_id"))
    sample = normalize_firmware(body, source_mode=device.source_mode)
    row, created = ingest_sample(db, sample, raw_payload=body)
    if created:
        db.add(Event(type="telemetry.ingested", entity_id=row.device_id, campus_id=row.campus_id))
    db.commit()
    return envelope({"device_id": row.device_id, "boot_epoch": row.boot_epoch, "sample_seq": row.sample_seq, "telemetry_id": row.id,
        "status": "stored" if created else "duplicate", "quality": row.quality, "quality_flags": row.quality_flags, "durable": True})


@router.get("/overview", tags=["analytics"])
def overview_route(request: Request, db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None):
    return envelope(overview(db, request.app.state.settings, campus_id, building_id))


@router.get("/energy/summary", response_model=Envelope[EnergySummaryResponse], response_model_exclude_unset=True, tags=["accounting"])
def energy_summary(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, start: datetime | None=None, end: datetime | None=None, device_ids: str | None=None):
    return envelope(compute_energy(db, **scope_dict(campus_id, building_id, start, end, device_ids)))


@router.get("/energy/breakdown", response_model=Envelope[list[EnergyBreakdownResponse]], response_model_exclude_unset=True, tags=["accounting"])
def energy_breakdown(db: DB, user: Read, group_by: Literal["building", "device", "circuit"]="building", campus_id: str | None=None, building_id: str | None=None, start: datetime | None=None, end: datetime | None=None):
    return envelope(breakdown(db, group_by, **scope_dict(campus_id, building_id, start, end)))


@router.get("/energy/balance", response_model=Envelope[EnergyBalanceResponse], response_model_exclude_unset=True, tags=["accounting"])
def energy_balance(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, start: datetime | None=None, end: datetime | None=None):
    return envelope(balance(db, **scope_dict(campus_id, building_id, start, end)))


@router.get("/carbon/summary", response_model=Envelope[CarbonSummaryResponse], response_model_exclude_unset=True, tags=["accounting"])
def carbon_summary(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, start: datetime | None=None, end: datetime | None=None, device_ids: str | None=None):
    return envelope(apply_accounting(db, "carbon", **scope_dict(campus_id, building_id, start, end, device_ids)))


@router.get("/cost/summary", response_model=Envelope[CostSummaryResponse], response_model_exclude_unset=True, tags=["accounting"])
def cost_summary(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, start: datetime | None=None, end: datetime | None=None, device_ids: str | None=None, allocation_mode: Literal["strict","proportional_estimate"]="strict"):
    return envelope(apply_accounting(db, "cost", allocation_mode=allocation_mode, **scope_dict(campus_id, building_id, start, end, device_ids)))


@router.get("/carbon/factors", response_model=Envelope[list[FactorResponse]], response_model_exclude_unset=True, tags=["accounting"])
def factors(db: DB, user: Read, limit: Limit=100, offset: Offset=0):
    return paginated(db, select(CarbonFactor).order_by(CarbonFactor.valid_from.desc()), limit, offset)


def add_versioned_accounting(db, model, body, actor):
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        from .common import payload_hash
        # Serialize the empty-range check as well as existing rows; row locks alone
        # cannot prevent concurrent first versions from creating overlap.
        key=int(payload_hash({"configuration":model.__tablename__,"source_mode":body.source_mode})[:16],16)&((1<<63)-1)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"),{"key":key})
    if db.get(model, body.id):
        raise DomainError("immutable_version", "Accounting versions are immutable; use a new ID and nonoverlapping interval", 409)
    overlap = db.scalar(select(model).where(model.source_mode == body.source_mode, model.valid_from < body.valid_to, model.valid_to > body.valid_from).limit(1))
    if overlap:
        raise DomainError("overlapping_validity", "Validity interval overlaps an existing accounting version for this source mode", 409)
    row = model(**body.model_dump())
    db.add(row)
    audit(db, actor, "created", "carbon_factor" if model is CarbonFactor else "tariff", row.id, {"source_mode": body.source_mode, "version": body.version})
    db.commit()
    return row


@router.post("/carbon/factors", response_model=Envelope[FactorResponse], response_model_exclude_unset=True, status_code=201, tags=["accounting"])
def factor_create(body: FactorIn, db: DB, user: GlobalAdmin):
    return envelope(record_dict(add_versioned_accounting(db, CarbonFactor, body, user.id)))


@router.get("/tariffs", response_model=Envelope[list[TariffResponse]], response_model_exclude_unset=True, tags=["accounting"])
def tariffs(db: DB, user: Read, limit: Limit=100, offset: Offset=0):
    return paginated(db, select(Tariff).order_by(Tariff.valid_from.desc()), limit, offset)


@router.post("/tariffs", response_model=Envelope[TariffResponse], response_model_exclude_unset=True, status_code=201, tags=["accounting"])
def tariff_create(body: TariffIn, db: DB, user: GlobalAdmin):
    return envelope(record_dict(add_versioned_accounting(db, Tariff, body, user.id)))


@router.get("/commands", response_model=Envelope[list[CommandResponse]], response_model_exclude_unset=True, tags=["control"])
def commands(db: DB, user: Read, device_id: str | None=None, status: str | None=None, campus_id: str | None=None, building_id: str | None=None, limit: Limit=100, offset: Offset=0):
    query = select(Command)
    if campus_id:
        query = query.where(Command.campus_id == campus_id)
    if building_id:
        query = query.where(Command.building_id == building_id)
    if device_id:
        query = query.where(Command.device_id == device_id)
    if status:
        query = query.where(Command.status == status)
    return paginated(db, query.order_by(Command.issued_at.desc()), limit, offset, command_dict)


@router.post("/commands", response_model=Envelope[CommandResponse], response_model_exclude_unset=True, responses={200: {"model": Envelope[CommandResponse], "description": "Existing idempotent command"}}, status_code=201, tags=["control"])
def command_create(body: CommandIn, request: Request, response: Response, db: DB, user: Operate, idempotency_key: str | None=Header(default=None)):
    command, created = create_command(db, body, idempotency_key, user.id, settings=request.app.state.settings)
    db.commit()
    if not created:
        response.status_code = 200
    return envelope(command_dict(command), created=created)


@router.get("/commands/{command_id}", response_model=Envelope[CommandResponse], response_model_exclude_unset=True, tags=["control"])
def command_detail(command_id: str, db: DB, user: Read):
    return envelope(command_dict(require_entity(db, Command, command_id)))


@router.get("/alarms", tags=["operations"])
def alarms(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, status: Literal["open", "acknowledged", "resolved"] | None=None, severity: Literal["info", "warning", "critical"] | None=None, limit: Limit=100, offset: Offset=0):
    query = select(Alarm)
    for key, value in {"campus_id": campus_id, "building_id": building_id, "status": status, "severity": severity}.items():
        if value:
            query = query.where(getattr(Alarm, key) == value)
    return paginated(db, query.order_by(Alarm.created_at.desc()), limit, offset)


@router.get("/alarms/{alarm_id}", tags=["operations"])
def alarm_detail(alarm_id: str, db: DB, user: Read):
    return envelope(record_dict(require_entity(db, Alarm, alarm_id)))


@router.post("/alarms/{alarm_id}/acknowledge", tags=["operations"])
def alarm_ack(alarm_id: str, body: NoteIn, db: DB, user: Operate):
    alarm = locked_entity(db, Alarm, alarm_id)
    if alarm.status == "resolved":
        raise DomainError("alarm_resolved", "A resolved alarm cannot be acknowledged", 409)
    if alarm.status == "open":
        alarm.status, alarm.acknowledged_at, alarm.acknowledged_by = "acknowledged", utcnow(), user.id
        if body.note:
            alarm.notes = [*alarm.notes, {"at": iso(utcnow()), "by": user.id, "text": body.note}]
        audit(db, user.id, "acknowledged", "alarm", alarm.id, {"note": body.note})
    db.commit()
    return envelope(record_dict(alarm))


@router.post("/alarms/{alarm_id}/resolve", tags=["operations"])
def alarm_resolve(alarm_id: str, body: RequiredNote, db: DB, user: Operate):
    alarm = locked_entity(db, Alarm, alarm_id)
    if alarm.status == "open":
        raise DomainError("acknowledgement_required", "Acknowledge the alarm before resolving it", 409)
    if alarm.status != "resolved":
        alarm.status, alarm.resolved_at, alarm.resolved_by = "resolved", utcnow(), user.id
        alarm.notes = [*alarm.notes, {"at": iso(utcnow()), "by": user.id, "text": body.note}]
        audit(db, user.id, "resolved", "alarm", alarm.id, {"note": body.note})
    db.commit()
    return envelope(record_dict(alarm))


@router.post("/alarms/{alarm_id}/notes", tags=["operations"])
def alarm_note(alarm_id: str, body: RequiredNote, db: DB, user: Operate):
    alarm = locked_entity(db, Alarm, alarm_id)
    alarm.notes = [*alarm.notes, {"at": iso(utcnow()), "by": user.id, "text": body.note}]
    audit(db, user.id, "note_added", "alarm", alarm.id)
    db.commit()
    return envelope(record_dict(alarm))


@router.get("/forecasts", response_model=Envelope[ForecastResponse], response_model_exclude_unset=True, tags=["strategy"])
def forecasts(request: Request, db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, horizon_hours: int=Query(default=24, ge=1, le=72)):
    from .forecast_jobs import cached_forecast
    return envelope(cached_forecast(db,request.app.state.settings,user,campus_id,building_id,horizon_hours))


from .schemas import ForecastRefreshIn


@router.post("/forecasts/refresh", response_model=Envelope[ForecastResponse], response_model_exclude_unset=True, tags=["strategy"])
def forecast_refresh(body: ForecastRefreshIn, request: Request, db: DB, user: Read):
    from .forecast_jobs import cached_forecast
    return envelope(cached_forecast(db,request.app.state.settings,user,**body.model_dump(),retry=True))


@router.get("/strategies", tags=["strategy"])
def strategies(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, limit: Limit=100, offset: Offset=0):
    query=select(Strategy)
    if campus_id:
        query=query.where(Strategy.campus_id==campus_id)
    if building_id:
        query=query.where(Strategy.building_id==building_id)
    return paginated(db, query.order_by(Strategy.created_at.desc()), limit, offset)


@router.post("/strategies", status_code=201, tags=["strategy"])
def strategy_create(body: StrategyIn, db: DB, user: Analyze):
    validate_binding(db, {"campus_id": body.campus_id, "building_id": body.building_id})
    strategy = Strategy(id=uid("strategy"), **body.model_dump(), created_by=user.id)
    db.add(strategy)
    audit(db, user.id, "created", "strategy", strategy.id)
    db.commit()
    return envelope(record_dict(strategy))


@router.post("/strategies/{strategy_id}/evaluate", tags=["strategy"])
def strategy_evaluate(strategy_id: str, db: DB, user: Analyze):
    strategy = locked_entity(db, Strategy, strategy_id)
    result = evaluate_strategy(db, strategy, user.id)
    db.commit()
    return envelope(result)


@router.post("/strategies/{strategy_id}/approve", tags=["strategy"])
def strategy_approve(strategy_id: str, body: RequiredNote, db: DB, user: Admin):
    strategy = locked_entity(db, Strategy, strategy_id)
    if not strategy.latest_evaluation or strategy.latest_evaluation["quality"] == "insufficient_data":
        raise DomainError("evaluation_required", "A usable shadow evaluation is required before approval", 409)
    strategy.status, strategy.approved_at, strategy.approved_by = "approved", utcnow(), user.id
    audit(db, user.id, "approved", "strategy", strategy.id, {"note": body.note, "evaluation_id": strategy.latest_evaluation["id"], "dispatch_performed": False})
    db.commit()
    return envelope(record_dict(strategy))


def report_visible(user, report):
    if user.campus_ids is None:
        return True
    scope = report.parameters.get("authorized_campus_ids")
    if scope is None and report.campus_id:
        scope = [report.campus_id]
    return scope is not None and set(scope).issubset(set(user.campus_ids))


@router.get("/reports", tags=["reports"])
def reports(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, limit: Limit=100, offset: Offset=0):
    query=select(Report)
    if campus_id:
        query=query.where(Report.campus_id==campus_id)
    if building_id:
        query=query.where(Report.parameters["building_id"].as_string()==building_id)
    from .scoping import report_scope_predicate
    from sqlalchemy.orm import load_only
    query=query.where(report_scope_predicate(db,user)).options(load_only(Report.id,Report.name,Report.type,Report.created_at,Report.created_by,Report.source_mode,Report.campus_id,Report.parameters,Report.summary))
    return paginated(db,query.order_by(Report.created_at.desc()),limit,offset,lambda row:record_dict(row,exclude=("content",)))


@router.post("/reports", status_code=201, tags=["reports"])
def report_create(body: ReportIn, request: Request, db: DB, user: Analyze):
    scope = {"campus_id": body.campus_id, "building_id": body.building_id, "start": body.start, "end": body.end}
    if body.type == "operations":
        content = overview(db, request.app.state.settings, body.campus_id, body.building_id)
        summary = content["counts"]
        source_mode = content["source_mode"]
    else:
        content = compute_energy(db, **scope) if body.type == "energy" else apply_accounting(db, body.type, allocation_mode=body.cost_allocation_mode, **scope)
        content["breakdown"] = breakdown(db, "building", **scope)
        summary = {key: value for key, value in content.items() if key not in {"breakdown", "selected_device_ids", "factor", "tariff"}}
        source_mode = content["source_mode"]
    report = Report(id=uid("report"), name=body.name, type=body.type, created_by=user.id, source_mode=source_mode, campus_id=body.campus_id or (require_entity(db, Building, body.building_id).campus_id if body.building_id else None), parameters={**body.model_dump(mode="json"), "authorized_campus_ids": [body.campus_id] if body.campus_id else ([require_entity(db, Building, body.building_id).campus_id] if body.building_id else user.campus_ids)}, summary=summary, content=content)
    db.add(report)
    audit(db, user.id, "created", "report", report.id, {"type": body.type, "source_mode": source_mode})
    db.commit()
    return envelope(record_dict(report))


@router.get("/reports/{report_id}", tags=["reports"])
def report_detail(report_id: str, db: DB, user: Read):
    report = require_entity(db, Report, report_id)
    if not report_visible(user, report):
        raise DomainError("not_found", "Report not found", 404)
    return envelope(record_dict(report))


@router.get("/reports/{report_id}/export", tags=["reports"])
def report_export(report_id: str, db: DB, user: Read, format: Literal["json", "csv"]="json"):
    report = require_entity(db, Report, report_id)
    if not report_visible(user, report):
        raise DomainError("not_found", "Report not found", 404)
    if format == "json":
        content, media = json.dumps(record_dict(report), ensure_ascii=False, indent=2), "application/json"
    else:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["metric", "value", "source_mode"])
        for key, value in report.summary.items():
            # Spreadsheet formula injection is neutralized even for operator-authored names.
            text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
            if text.startswith(("=", "+", "-", "@", "\t", "\r")):
                text = "'" + text
            writer.writerow([key, text, report.source_mode])
        content, media = "\ufeff" + buffer.getvalue(), "text/csv; charset=utf-8"
    return Response(content, media_type=media, headers={"Content-Disposition": f'attachment; filename="{report.id}.{format}"'})


@router.get("/audit", tags=["system"])
def audit_log(db: DB, user: Read, entity_type: str | None=None, entity_id: str | None=None, campus_id: str | None=None, limit: Limit=100, offset: Offset=0):
    query = select(Audit)
    if campus_id:
        query = query.where(Audit.campus_id == campus_id)
    if entity_type:
        query = query.where(Audit.entity_type == entity_type)
    if entity_id:
        query = query.where(Audit.entity_id == entity_id)
    return paginated(db, query.order_by(Audit.id.desc()), limit, offset)


@router.get("/settings", tags=["system"])
def settings_read(request: Request, db: DB, user: Read):
    stale, offline = freshness_limits(db, request.app.state.settings)
    return envelope({"stale_after_seconds": stale, "offline_after_seconds": offline, "physical_control_enabled": request.app.state.settings.physical_dispatch_enabled,
        "session_hours": request.app.state.settings.session_hours, "simulation_enabled": request.app.state.settings.simulation_enabled, "timezone": "UTC", "measurement_timezone": "Asia/Shanghai"})


@router.patch("/settings", tags=["system"])
def settings_update(body: SettingsPatch, request: Request, db: DB, user: GlobalAdmin):
    stale, offline = freshness_limits(db, request.app.state.settings)
    values = {"stale_after_seconds": stale, "offline_after_seconds": offline, **body.model_dump(exclude_none=True)}
    if values["offline_after_seconds"] <= values["stale_after_seconds"]:
        raise DomainError("invalid_thresholds", "Offline threshold must exceed stale threshold", 422)
    state = db.get(State, "settings")
    if state:
        state.value = values
    else:
        db.add(State(key="settings", value=values))
    audit(db, user.id, "updated", "settings", "operational", values)
    db.commit()
    return settings_read(request, db, user)


@router.get("/system/status", tags=["system"])
def system_status(request: Request, db: DB, user: Read):
    settings = request.app.state.settings
    from .spatial import spatial_status
    worker = db.get(State, "worker")
    worker_value = worker.value if worker else {}
    analysis=db.get(State,"analysis_worker")
    analysis_value=analysis.value if analysis else {}
    analysis_status="running" if analysis and utcnow().timestamp()-analysis_value.get("last_tick_epoch",0)<180 else "stale" if analysis else "not_started"
    worker_status = "running" if worker_value and utcnow().timestamp()-worker_value.get("last_tick_epoch", 0) < max(10, settings.worker_interval_seconds*5) else "stale" if worker else "not_started"
    return envelope({"mode": settings.env, "version": __version__, "database": {"status": "connected", "dialect": db.bind.dialect.name},
        "worker": {"status": worker_status, "last_tick_at": worker_value.get("last_tick_at")},
        "analysis": {"status":analysis_status,"last_tick_at":analysis_value.get("last_tick_at"),"http_training":False,"physical_actions":False},
        "ingestion": {"last_received_at": iso(db.scalar(select(func.max(Telemetry.received_at)))), "total_samples": db.scalar(select(func.count()).select_from(Telemetry))},
        "physical_control": {"enabled": settings.physical_dispatch_enabled, "reason": "Independent deployment gate configured; per-device release and runtime guards still required" if settings.physical_dispatch_enabled else "Independent physical deployment release gate is closed", "hardware_connection_verified": False},
        "spatial": spatial_status(db, settings), "simulation": {"enabled": settings.simulation_enabled, "source_mode": "SIMULATED"},
        "warnings": (["SQLite is development/test only"] if db.bind.dialect.name == "sqlite" else []) + (["Development authentication fixtures are enabled; bind deployment to loopback"] if settings.dev_auth else [])})


@router.get("/events", tags=["system"])
async def events(request: Request, db: DB, user: Read, after_id: int=Query(default=0, ge=0)):
    try:
        cursor = max(after_id, int(request.headers.get("Last-Event-ID", "0")))
    except ValueError:
        raise DomainError("invalid_event_cursor", "Last-Event-ID must be an integer", 422)
    expires = request.state.auth_session.expires_at
    session_hash = request.state.auth_session.token_hash
    db.commit()  # Never hold a database transaction during the SSE stream
    async def stream():
        nonlocal cursor
        # Finite connections force auth revalidation and permit orderly proxy restarts.
        deadline = utcnow()+timedelta(seconds=25)
        while utcnow() < min(deadline, expires):
            if await request.is_disconnected():
                break
            with request.app.state.session_factory() as db:
                current_session = db.get(Session, session_hash)
                if not current_session or current_session.expires_at <= utcnow():
                    break
                live_user = db.get(User, current_session.user_id)
                if not live_user or not live_user.enabled or live_user.role not in {"admin", "operator", "analyst", "viewer"} or (live_user.is_dev_fixture and not request.app.state.settings.dev_auth):
                    break
                db.info["campus_ids"], db.info["actor"] = live_user.campus_ids, live_user.id
                rows = list(db.scalars(select(Event).where(Event.id > cursor).order_by(Event.id).limit(100)))
            if rows:
                for row in rows:
                    cursor = row.id
                    yield f"id: {row.id}\nevent: change\ndata: {json.dumps(record_dict(row))}\n\n"
            else:
                yield ": heartbeat\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.get("/adapter/commands", tags=["adapters"])
def adapter_commands(request: Request, db: DB, limit: int=Query(default=20, ge=1, le=100), adapter=Depends(adapter_auth)):
    from .adapter import poll_commands
    allowed = request.app.state.settings.adapter_allowed_device_ids
    if not allowed:
        raise DomainError("adapter_scope_unconfigured", "Configure an explicit adapter device allowlist", 503)
    result = poll_commands(db, request.app.state.settings, allowed, limit)
    db.commit()
    return envelope(result)


from .schemas import DeliveryIn, DispatchIn, UserIn, UserPatch, PasswordIn
from .models import User
from .security import password_hash, user_payload


@router.post("/adapter/commands/{command_id}/delivery", tags=["adapters"])
def adapter_delivery(command_id: str, body: DeliveryIn, request: Request, db: DB, adapter=Depends(adapter_auth)):
    from .adapter import record_delivery
    result = record_delivery(db, command_id, body, request.app.state.settings.adapter_allowed_device_ids)
    db.commit()
    return envelope(result)


@router.post("/ingest/ack", tags=["adapters"])
def adapter_ack(body: dict, request: Request, db: DB, adapter=Depends(adapter_auth)):
    from .adapter import store_ack
    if body.get("device_id") not in request.app.state.settings.adapter_allowed_device_ids:
        raise DomainError("adapter_scope_denied", "Adapter is not authorized for this identity", 403)
    device = require_entity(db, Device, body.get("device_id"))
    if device.dispatch_mode == "IN_PROCESS":
        raise DomainError("adapter_mode_mismatch", "External acknowledgements cannot verify in-process simulation commands", 409)
    observation, created = store_ack(db, body)
    db.commit()
    return envelope({"id": observation.command_id, "device_id": observation.device_id, "seq": observation.sequence,
        "durable": True, "status": "stored" if created else "duplicate", "matched": observation.matched})


@router.post("/strategies/{strategy_id}/dispatch", status_code=201, tags=["strategy"])
def strategy_dispatch(strategy_id: str, body: DispatchIn, request: Request, db: DB, user: Operate, idempotency_key: str | None=Header(default=None)):
    strategy = db.scalar(select(Strategy).where(Strategy.id == strategy_id).with_for_update().execution_options(populate_existing=True))
    if not strategy:
        raise DomainError("not_found", "Strategy not found", 404)
    evaluation = strategy.latest_evaluation
    if strategy.status != "approved" or not evaluation or evaluation["id"] != body.evaluation_id:
        raise DomainError("approval_required", "Dispatch requires approval of this exact frozen evaluation", 409)
    evaluated_at = datetime.fromisoformat(evaluation["created_at"].replace("Z", "+00:00"))
    if utcnow()-evaluated_at > timedelta(minutes=5):
        raise DomainError("evaluation_expired", "Evaluate and approve again; the frozen plan is older than five minutes", 409)
    if not evaluation["candidate_device_ids"]:
        raise DomainError("no_candidates", "Evaluation has no eligible candidates", 409)
    if not idempotency_key or not 8 <= len(idempotency_key) <= 80:
        raise DomainError("idempotency_key_required", "Supply an 8–80 character Idempotency-Key header", 422)
    results = []
    for device_id in sorted(evaluation["candidate_device_ids"]):
        device = require_entity(db, Device, device_id)
        if device.source_mode != "SIMULATED":
            raise DomainError("physical_strategy_dispatch_disabled", "Strategy dispatch is currently restricted to explicitly simulated devices", 409)
        command, _ = create_command(db, CommandIn(device_id=device_id, action="shed", expires_in_seconds=30, reason=body.reason),
            f"strategy:{idempotency_key}:{device_id}", user.id, settings=request.app.state.settings)
        results.append(command_dict(command))
    audit(db, user.id, "dispatch_requested", "strategy", strategy.id, {"evaluation_id": evaluation["id"], "command_ids": [c["id"] for c in results], "source_mode": "SIMULATED"})
    db.commit()
    return envelope({"evaluation_id": evaluation["id"], "commands": results, "source_mode": "SIMULATED", "physical_dispatch": False})


def visible_user(actor, target):
    if actor.campus_ids is None:
        return True
    return target.campus_ids is not None and set(target.campus_ids).issubset(set(actor.campus_ids))


def validate_user_scope(db, actor, campus_ids):
    if actor.campus_ids is not None and (campus_ids is None or not set(campus_ids).issubset(set(actor.campus_ids))):
        raise DomainError("scope_escalation", "Cannot grant broader campus access than your own", 403)
    for campus_id in campus_ids or []:
        require_entity(db, Campus, campus_id)


def safe_user(user):
    return {**user_payload(user), "enabled": user.enabled, "is_dev_fixture": user.is_dev_fixture}


@router.get("/users", tags=["administration"])
def users_list(db: DB, user: Admin, limit: Limit=100, offset: Offset=0):
    users = [u for u in db.scalars(select(User).order_by(User.username)) if visible_user(user, u)]
    return envelope([safe_user(u) for u in users[offset:offset+limit]], total=len(users), limit=limit, offset=offset)


@router.post("/users", status_code=201, tags=["administration"])
def user_create(body: UserIn, db: DB, user: Admin):
    validate_user_scope(db, user, body.campus_ids)
    if db.scalar(select(User).where(User.username == body.username)):
        raise DomainError("already_exists", "Username already exists", 409)
    target = User(id=uid("user"), username=body.username, display_name=body.display_name, role=body.role, campus_ids=body.campus_ids,
        password_hash=password_hash(body.password), is_dev_fixture=False)
    db.add(target)
    audit(db, user.id, "created", "user", target.id, {"role": body.role, "campus_ids": body.campus_ids})
    db.commit()
    return envelope(safe_user(target))


@router.patch("/users/{user_id}", tags=["administration"])
def user_update(user_id: str, body: UserPatch, db: DB, user: Admin):
    from sqlalchemy import delete
    target = locked_entity(db, User, user_id)
    if not visible_user(user, target):
        raise DomainError("not_found", "User not found", 404)
    changes = body.model_dump(exclude_unset=True)
    if "campus_ids" in changes:
        validate_user_scope(db, user, changes["campus_ids"])
    if any(changes.get(key, False) is None for key in ("display_name", "role", "enabled")):
        raise DomainError("invalid_patch", "Only campus_ids may be explicitly null", 422)
    removes_global_admin = target.role == "admin" and target.enabled and target.campus_ids is None and (
        changes.get("role", target.role) != "admin" or changes.get("enabled") is False or ("campus_ids" in changes and changes["campus_ids"] is not None))
    if removes_global_admin:
        enabled_admins = list(db.scalars(select(User).where(User.role == "admin", User.enabled.is_(True)).order_by(User.id).with_for_update().execution_options(populate_existing=True)))
        remaining_global = [u for u in enabled_admins if u.id != target.id and u.campus_ids is None]
        if not remaining_global:
            raise DomainError("last_global_administrator", "At least one enabled global administrator must remain", 409)
    if target.role == "admin" and target.enabled and (changes.get("role", target.role) != "admin" or changes.get("enabled") is False):
        remaining = db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.enabled.is_(True), User.id != target.id))
        if remaining == 0:
            raise DomainError("last_administrator", "Cannot disable or demote the last enabled administrator", 409)
    for key, value in changes.items():
        setattr(target, key, value)
    db.execute(delete(Session).where(Session.user_id == target.id))
    audit(db, user.id, "updated", "user", target.id, changes)
    db.commit()
    return envelope(safe_user(target), sessions_revoked=True)


@router.post("/users/{user_id}/password", tags=["administration"])
def user_password(user_id: str, body: PasswordIn, db: DB, user: Admin):
    from sqlalchemy import delete
    target = locked_entity(db, User, user_id)
    if not visible_user(user, target):
        raise DomainError("not_found", "User not found", 404)
    if target.is_dev_fixture:
        raise DomainError("fixture_account", "Development fixtures cannot become production credentials; create a managed user", 409)
    target.password_hash = password_hash(body.password)
    db.execute(delete(Session).where(Session.user_id == target.id))
    audit(db, user.id, "password_reset", "user", target.id, {"sessions_revoked": True})
    db.commit()
    return envelope({"user_id": target.id, "sessions_revoked": True})


from .schemas import CircuitPatch, ScheduleIn, ScheduleImport
from .models import ScheduleEvent
from .scheduling import create_schedule, schedule_dict, validate_schedule


@router.patch("/circuits/{circuit_id}", tags=["registry"])
def circuit_update(circuit_id: str, body: CircuitPatch, db: DB, user: Operate):
    circuit = require_entity(db, Circuit, circuit_id)
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes:
        if changes["name"] is None:
            raise DomainError("invalid_patch", "Circuit name cannot be null", 422)
        circuit.name = changes["name"]
    if "parent_id" in changes and changes["parent_id"] != circuit.parent_id:
        # Serialize topology changes within this building to prevent concurrent
        # A→B/B→A edits from each independently passing a cycle check.
        list(db.scalars(select(Circuit).where(Circuit.campus_id == circuit.campus_id, Circuit.building_id == circuit.building_id).order_by(Circuit.id).with_for_update().execution_options(populate_existing=True)))
        all_circuits = list(db.scalars(select(Circuit).where(Circuit.campus_id == circuit.campus_id, Circuit.building_id == circuit.building_id)))
        descendants = {circuit.id}
        while True:
            expanded = descendants | {row.id for row in all_circuits if row.parent_id in descendants}
            if expanded == descendants:
                break
            descendants = expanded
        if db.scalar(select(Telemetry.id).where(Telemetry.circuit_id.in_(descendants)).limit(1)):
            raise DomainError("immutable_measurement_boundary", "Historical circuit or descendant measurement boundaries cannot be rewritten; create a new circuit and dated device binding", 409)
        parent_id, seen = changes["parent_id"], {circuit.id}
        while parent_id:
            if parent_id in seen:
                raise DomainError("topology_cycle", "A circuit cannot be its own ancestor", 409)
            seen.add(parent_id)
            parent = require_entity(db, Circuit, parent_id)
            if parent.campus_id != circuit.campus_id or parent.building_id != circuit.building_id or parent.source_mode != circuit.source_mode:
                raise DomainError("topology_mismatch", "Parent circuit must share campus, building and source mode", 409)
            parent_id = parent.parent_id
        circuit.parent_id = changes["parent_id"]
    audit(db, user.id, "updated", "circuit", circuit.id, changes)
    db.commit()
    return envelope(record_dict(circuit))


@router.get("/schedules", tags=["scheduling"])
def schedules(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, space_id: str | None=None,
              start: datetime | None=None, end: datetime | None=None, limit: Limit=100, offset: Offset=0):
    start, end = period(start, end)
    query = select(ScheduleEvent).where(ScheduleEvent.starts_at < end, ScheduleEvent.ends_at > start)
    for key, value in {"campus_id": campus_id, "building_id": building_id, "space_id": space_id}.items():
        if value:
            query = query.where(getattr(ScheduleEvent, key) == value)
    return paginated(db, query.order_by(ScheduleEvent.starts_at), limit, offset, schedule_dict)


@router.post("/schedules", status_code=201, tags=["scheduling"])
def schedule_create(body: ScheduleIn, db: DB, user: Operate):
    row = create_schedule(db, body.model_dump(), user.id)
    db.commit()
    return envelope(schedule_dict(row))


@router.post("/schedules/import", status_code=201, tags=["scheduling"])
def schedule_import(body: ScheduleImport, db: DB, user: Operate):
    rows = [create_schedule(db, event.model_dump(), user.id) for event in body.events]
    db.commit()
    return envelope([schedule_dict(row) for row in rows], imported=len(rows), observed_occupancy="unknown")


@router.put("/schedules/{schedule_id}", tags=["scheduling"])
def schedule_update(schedule_id: str, body: ScheduleIn, db: DB, user: Operate):
    row = locked_entity(db, ScheduleEvent, schedule_id)
    validate_schedule(db, body.model_dump())
    if body.campus_id != row.campus_id:
        raise DomainError("schedule_scope_immutable", "Cancel the original event and create a new campus-scoped event for cross-campus relocation", 409)
    before = schedule_dict(row)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.revision += 1
    audit(db, user.id, "updated", "schedule", row.id, {"before": before, "revision": row.revision})
    db.commit()
    return envelope(schedule_dict(row))


@router.post("/schedules/{schedule_id}/cancel", tags=["scheduling"])
def schedule_cancel(schedule_id: str, body: RequiredNote, db: DB, user: Operate):
    row = locked_entity(db, ScheduleEvent, schedule_id)
    if row.status != "cancelled":
        row.status = "cancelled"
        row.revision += 1
        audit(db, user.id, "cancelled", "schedule", row.id, {"note": body.note, "revision": row.revision})
    db.commit()
    return envelope(schedule_dict(row))


from .schemas import CommissioningIn, ReleaseIn
from .models import CommissioningRecord


@router.get("/devices/{device_id}/commissioning", tags=["commissioning"])
def commissioning_list(device_id: str, db: DB, user: Read):
    require_entity(db, Device, device_id)
    return envelope([record_dict(row) for row in db.scalars(select(CommissioningRecord).where(CommissioningRecord.device_id == device_id).order_by(CommissioningRecord.created_at.desc()))])


@router.post("/devices/{device_id}/commissioning", status_code=201, tags=["commissioning"])
def commissioning_create(device_id: str, body: CommissioningIn, db: DB, user: Admin):
    from .commissioning import create_record
    row = create_record(db, locked_entity(db, Device, device_id), body, user.id)
    db.commit()
    return envelope(record_dict(row))


@router.post("/devices/{device_id}/commissioning/release", tags=["commissioning"])
def commissioning_release(device_id: str, body: ReleaseIn, request: Request, db: DB, user: Admin):
    from .commissioning import release_device
    row = release_device(db, locked_entity(db, Device, device_id), body, request.app.state.settings, user.id)
    db.commit()
    return envelope(record_dict(row), automatic_safety_certification=False)


@router.post("/devices/{device_id}/commissioning/{release_id}/revoke", tags=["commissioning"])
def commissioning_revoke(device_id: str, release_id: str, body: RequiredNote, db: DB, user: Admin):
    from .commissioning import revoke_release
    row = revoke_release(db, locked_entity(db, Device, device_id), require_entity(db, CommissioningRecord, release_id), user.id, body.note)
    db.commit()
    return envelope(record_dict(row), in_flight_delivery_may_be_uncertain=True)


@router.get("/assets/product/manifest", tags=["registry"])
def product_manifest(request: Request, user: Read, family: Literal["PLUG", "SWITCH", "PRESENCE"]):
    from .product_assets import product_files
    manifest,_=product_files(request.app.state.settings.product_asset_dir,family)
    return envelope(manifest)


@router.get("/assets/product/model", tags=["registry"])
def product_model(request: Request, db: DB, user: Read, family: Literal["PLUG", "SWITCH", "PRESENCE"]):
    from fastapi.responses import FileResponse
    from .product_assets import product_files,verify_asset
    manifest,paths=product_files(request.app.state.settings.product_asset_dir,family)
    digest=verify_asset(paths["model"],manifest,"model")
    db.commit()
    return FileResponse(paths["model"],media_type="model/gltf-binary",headers={"ETag":'"'+digest+'"',"Cache-Control":"private, max-age=3600"})


@router.get("/assets/product/hero", tags=["registry"])
def product_hero(request: Request, db: DB, user: Read, family: Literal["PLUG", "SWITCH", "PRESENCE"]):
    from fastapi.responses import FileResponse
    from .product_assets import product_files,verify_asset
    manifest,paths=product_files(request.app.state.settings.product_asset_dir,family)
    digest=verify_asset(paths["hero"],manifest,"hero")
    db.commit()
    return FileResponse(paths["hero"],media_type="image/png",headers={"ETag":'"'+digest+'"',"Cache-Control":"private, max-age=3600"})


@router.get("/devices/{device_id}/control-eligibility", response_model=Envelope[ControlEligibilityResponse], response_model_exclude_unset=True, tags=["control"])
def control_eligibility(device_id: str, request: Request, db: DB, user: Read, channel_id: str | None=None):
    from .control import eligibility
    device=require_entity(db,Device,device_id)
    settings=request.app.state.settings
    release=db.get(CommissioningRecord,device.physical_release_id) if device.physical_release_id else None
    reasons={}
    for action in ("hold","shed","restore"):
        reasons[action]="role_forbidden" if user.role not in {"admin","operator"} else eligibility(db,device,action=action,settings=settings,channel_id=channel_id)
    allowed=[action for action,reason in reasons.items() if reason is None]
    load=device.provenance.get("load_binding",{})
    load_id=release.load_id if release else load.get("id")
    load_name=release.load_name if release else load.get("name")
    if device.source_mode=="SIMULATED" and not load_name:
        load_id,load_name=f"sim-load:{device.id}",f"{device.name} · explicitly simulated load"
    from .channel_control import target_channel
    try:
        channel = target_channel(db, device, channel_id)
    except DomainError:
        channel = None
    return envelope({"channel_id":channel.id if channel else channel_id,"channel_key":channel.channel_key if channel else "relay.1",
        "product_family":"SWITCH" if device.kind in {"switch","light"} else "PLUG",
        "verification_kind":"actuator_reported_only" if device.kind in {"switch","light"} else "independent_feedback",
        "device_id":device.id,"device_name":device.name,"profile_revision":device.profile_revision,"source_mode":device.source_mode,"dispatch_mode":device.dispatch_mode,
        "eligible":bool(allowed),"allowed_actions":allowed,"reasons":reasons,"physical_deployment_enabled":settings.physical_dispatch_enabled,
        "load":{"id":load_id,"name":load_name,"profile_id":device.profile_id},
        "release":{"id":release.id,"status":release.status,"valid_until":iso(release.valid_until),"basis":"operator_attestation"} if release else None,
        "checked_at":iso(utcnow()),"server_rechecks_on_submission_and_lease":True,
        "consequence":"May physically interrupt or restore mains power to the named load; feedback never proves safe isolation" if device.source_mode=="REAL" else "Changes explicitly simulated output state only"})
