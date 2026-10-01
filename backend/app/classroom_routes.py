"""Authenticated, campus-scoped classroom API and separately allowlisted ingestion."""
from datetime import datetime
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from .common import envelope, record_dict, require_entity, DomainError, locked_entity
from .security import get_db, current_user, roles, adapter_auth
from .models import (Space, Device, DeviceChannel, ChannelObservation, RoomMode, RoomPolicy,
    RoomEvaluation, RoomAnomaly, HardwareEvent, Command, Binding)
from .responses import Envelope, ErrorEnvelope
from .schemas import RequiredNote
from .classroom_schemas import (ChannelIn, ChannelBatch, ModeIn, PolicyIn, RoomSnapshot, TimelineResponse,
    DistributionResponse, ModeResponse, PolicyResponse, EvaluationResponse, AnomalyResponse, EvaluateAnomaliesIn, ChannelDefinition, ChannelBatchReceipt, IoTEventReceipt, IoTAckReceipt, PolicyPatch, ChannelSnapshot, AnomalyRuleResponse, AnomalyRulePatch, AnomalyRuleBatchPatch)
from . import classrooms as service
from . import room_control
from .db import utcnow, iso

router = APIRouter(prefix="/api/v1", tags=["classrooms"], responses={c: {"model": ErrorEnvelope} for c in (400,401,403,404,409,413,422,500)})
DB = Annotated[object, Depends(get_db)]
Read = Annotated[object, Depends(current_user)]
Operate = Annotated[object, Depends(roles("admin", "operator"))]
Admin = Annotated[object, Depends(roles("admin"))]
Limit = Annotated[int, Query(ge=1, le=2000)]
Offset = Annotated[int, Query(ge=0)]


def page(db, query, limit, offset, serialize=record_dict):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    return envelope([serialize(r) for r in db.scalars(query.limit(limit).offset(offset))], total=total, limit=limit, offset=offset)


@router.get("/classrooms", response_model=Envelope[list[RoomSnapshot]])
def rooms(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, floor_id: str | None=None,
    at: datetime | None=None, limit: Limit=2000, offset: Offset=0):
    query = service.room_query(campus_id, building_id, floor_id)
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    spaces = list(db.scalars(query.limit(limit).offset(offset)))
    return envelope(service.snapshots(db, spaces, at), total=total, limit=limit, offset=offset)


@router.get("/classrooms/distribution", response_model=Envelope[DistributionResponse])
def distribution(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, floor_id: str | None=None,
    at: datetime | None=None, start: datetime | None=None, end: datetime | None=None, group_by: Literal["campus", "building", "floor"]="building"):
    spaces = list(db.scalars(service.room_query(campus_id, building_id, floor_id)))
    return envelope(service.distribution(db, spaces, group_by, at, start, end))


@router.patch("/classrooms/anomaly-rules/batch", response_model=Envelope[list[AnomalyRuleResponse]])
def change_anomaly_rules(body: AnomalyRuleBatchPatch, db: DB, user: Operate):
    from .room_rules import patch_rule
    values=body.model_dump(exclude_unset=True,exclude={"room_ids","expected_revisions"})
    results=[]
    for room_id in sorted(body.room_ids):
        patch=AnomalyRulePatch(**values,expected_revision=body.expected_revisions[room_id])
        results.append(patch_rule(db,require_entity(db,Space,room_id),patch,user.id))
    db.commit()
    return envelope(results)


@router.get("/classrooms/anomalies", response_model=Envelope[list[AnomalyResponse]])
def anomalies(db: DB, user: Read, campus_id: str | None=None, building_id: str | None=None, space_id: str | None=None,
    status: Literal["open", "acknowledged", "resolved"] | None=None, limit: Limit=2000, offset: Offset=0):
    query = select(RoomAnomaly)
    for key, value in (("campus_id", campus_id), ("building_id", building_id), ("space_id", space_id), ("status", status)):
        if value:
            query = query.where(getattr(RoomAnomaly, key) == value)
    return page(db, query.order_by(RoomAnomaly.last_observed_at.desc(), RoomAnomaly.id), limit, offset)


@router.post("/classrooms/anomalies/evaluate", response_model=Envelope[list[AnomalyResponse]])
def evaluate_anomalies(body: EvaluateAnomaliesIn, db: DB, user: Operate):
    from .room_anomalies import evaluate_room
    query = service.room_query(body.campus_id, body.building_id, space_id=body.space_id)
    spaces = list(db.scalars(query))
    if len(spaces) > 2000:
        raise DomainError("scope_too_large", "Evaluate a scope with at most 2,000 rooms", 422)
    results, now = [], utcnow()
    for space in spaces:
        results.extend(evaluate_room(db, space, now))
    db.commit()
    return envelope([record_dict(r) for r in results], rooms_evaluated=len(spaces))


@router.post("/classrooms/anomalies/{anomaly_id}/acknowledge", response_model=Envelope[AnomalyResponse])
def acknowledge(anomaly_id: str, body: RequiredNote, db: DB, user: Operate):
    row = locked_entity(db, RoomAnomaly, anomaly_id)
    if row.status == "resolved":
        raise DomainError("invalid_transition", "Resolved anomaly cannot be acknowledged", 409)
    if row.status != "acknowledged":
        row.status = "acknowledged"
        row.notes = [*row.notes, {"at": iso(utcnow()), "by": user.id, "action": "acknowledged", "text": body.note}]
        service.audit_room(db, user.id, "acknowledged", require_entity(db, Space, row.space_id), "room_anomaly", row.id)
    db.commit()
    return envelope(record_dict(row))


@router.post("/classrooms/anomalies/{anomaly_id}/resolve", response_model=Envelope[AnomalyResponse])
def resolve(anomaly_id: str, body: RequiredNote, db: DB, user: Operate):
    row = locked_entity(db, RoomAnomaly, anomaly_id)
    if row.status != "resolved":
        row.status, row.resolved_at = "resolved", utcnow()
        row.notes = [*row.notes, {"at": iso(row.resolved_at), "by": user.id, "action": "resolved", "text": body.note}]
        service.audit_room(db, user.id, "resolved", require_entity(db, Space, row.space_id), "room_anomaly", row.id)
    db.commit()
    return envelope(record_dict(row))


@router.patch("/classrooms/policies/{policy_id}", response_model=Envelope[PolicyResponse])
def change_policy(policy_id: str, body: PolicyPatch, db: DB, user: Operate):
    policy = locked_entity(db, RoomPolicy, policy_id)
    if policy.enabled != body.enabled:
        policy.enabled = body.enabled
        policy.revision += 1
        service.audit_room(db, user.id, "enabled" if body.enabled else "disabled", require_entity(db, Space, policy.space_id),
            "room_policy", policy.id, {"revision": policy.revision, "reason": body.reason})
    db.commit()
    return envelope(record_dict(policy))


@router.post("/classrooms/policies/{policy_id}/evaluate", response_model=Envelope[EvaluationResponse])
def evaluate_policy(policy_id: str, request: Request, db: DB, user: Operate):
    policy = require_entity(db, RoomPolicy, policy_id)
    row = room_control.evaluate_policy(db, policy, user.id, settings=request.app.state.settings)
    db.commit()
    return envelope(room_control.evaluation_dict(db, row))


@router.get("/classrooms/evaluations/{evaluation_id}", response_model=Envelope[EvaluationResponse])
def evaluation(evaluation_id: str, db: DB, user: Read):
    return envelope(room_control.evaluation_dict(db, require_entity(db, RoomEvaluation, evaluation_id)))


@router.post("/classrooms/evaluations/{evaluation_id}/dispatch", response_model=Envelope[EvaluationResponse])
def dispatch(evaluation_id: str, request: Request, db: DB, user: Operate):
    row = room_control.dispatch_evaluation(db, require_entity(db, RoomEvaluation, evaluation_id), user.id, request.app.state.settings)
    db.commit()
    return envelope(room_control.evaluation_dict(db, row))


@router.get("/classrooms/{room_id}", response_model=Envelope[RoomSnapshot])
def room(room_id: str, db: DB, user: Read, at: datetime | None=None):
    return envelope(service.snapshots(db, [require_entity(db, Space, room_id)], at)[0])


@router.get("/classrooms/{room_id}/anomaly-rule", response_model=Envelope[AnomalyRuleResponse])
def anomaly_rule(room_id: str, db: DB, user: Read):
    from .room_rules import rule_for
    return envelope(rule_for(db, require_entity(db, Space, room_id)))


@router.patch("/classrooms/{room_id}/anomaly-rule", response_model=Envelope[AnomalyRuleResponse])
def change_anomaly_rule(room_id: str, body: AnomalyRulePatch, db: DB, user: Operate):
    from .room_rules import patch_rule
    result=patch_rule(db,require_entity(db,Space,room_id),body,user.id)
    db.commit()
    return envelope(result)


@router.get("/classrooms/{room_id}/channels", response_model=Envelope[list[ChannelSnapshot]])
def room_channels(room_id: str, db: DB, user: Read, at: datetime | None=None):
    return envelope(service.snapshots(db, [require_entity(db, Space, room_id)], at)[0]["channels"])


@router.get("/classrooms/{room_id}/evaluations", response_model=Envelope[list[EvaluationResponse]])
def room_evaluations(room_id: str, db: DB, user: Read, limit: Annotated[int, Query(ge=1, le=100)]=20, offset: Offset=0):
    require_entity(db, Space, room_id)
    return page(db, select(RoomEvaluation).where(RoomEvaluation.space_id == room_id).order_by(RoomEvaluation.at.desc(), RoomEvaluation.id),
        limit, offset, lambda row: room_control.evaluation_dict(db, row))


@router.get("/classrooms/{room_id}/timeline", response_model=Envelope[TimelineResponse])
def room_timeline(room_id: str, start: datetime, end: datetime, db: DB, user: Read):
    space = require_entity(db, Space, room_id)
    result = service.timeline(db, space, start, end)
    result["events"] = timeline_events(db, space, result["start"], result["end"])
    return envelope(result)


@router.get("/classrooms/{room_id}/mode", response_model=Envelope[list[ModeResponse]])
def modes(room_id: str, db: DB, user: Read):
    require_entity(db, Space, room_id)
    return envelope([record_dict(r) for r in db.scalars(select(RoomMode).where(RoomMode.space_id == room_id).order_by(RoomMode.starts_at.desc()).limit(1000))])


@router.patch("/classrooms/{room_id}/mode", response_model=Envelope[ModeResponse])
def change_mode(room_id: str, body: ModeIn, db: DB, user: Operate):
    row = service.set_mode(db, require_entity(db, Space, room_id), body, user.id)
    db.commit()
    return envelope(record_dict(row))


@router.get("/classrooms/{room_id}/policies", response_model=Envelope[list[PolicyResponse]])
def policies(room_id: str, db: DB, user: Read):
    require_entity(db, Space, room_id)
    return envelope([record_dict(r) for r in db.scalars(select(RoomPolicy).where(RoomPolicy.space_id == room_id).order_by(RoomPolicy.created_at.desc()).limit(1000))])


@router.post("/classrooms/{room_id}/policies", response_model=Envelope[PolicyResponse], status_code=201)
def new_policy(room_id: str, body: PolicyIn, db: DB, user: Operate):
    row = room_control.create_policy(db, require_entity(db, Space, room_id), body, user.id)
    db.commit()
    return envelope(record_dict(row))


@router.post("/channels", status_code=201, response_model=Envelope[ChannelDefinition])
def new_channel(body: ChannelIn, db: DB, user: Admin):
    row = service.register_channel(db, body, user.id)
    db.commit()
    return envelope(record_dict(row))


@router.post("/ingest/channels", tags=["ingestion"], response_model=Envelope[ChannelBatchReceipt])
def channel_samples(body: ChannelBatch, request: Request, db: DB, adapter=Depends(adapter_auth)):
    allowed = request.app.state.settings.adapter_allowed_device_ids
    receipts = []
    for sample in body.samples:
        channel = require_entity(db, DeviceChannel, sample.channel_id)
        if channel.device_id not in allowed:
            raise DomainError("adapter_scope_denied", "Adapter is not authorized for this channel", 403)
        row, created = service.ingest_channel(db, sample)
        receipts.append({"channel_id": row.channel_id, "observation_id": row.id, "status": "stored" if created else "duplicate", "quality": row.quality})
    db.commit()
    return envelope({"durable": True, "receipts": receipts})


def contract_request(kind):
    import json
    from .iot_ingestion import contract
    schema = json.loads((contract().SCHEMAS / f"{kind}.schema.json").read_text(encoding="utf-8"))
    schema.pop("$schema", None)
    schema.pop("$id", None)
    return {"requestBody": {"required": True, "content": {"application/json": {"schema": schema}}}}


@router.post("/ingest/events", tags=["ingestion"], response_model=Envelope[IoTEventReceipt], openapi_extra=contract_request("event"))
def canonical_event(body: dict, request: Request, db: DB, adapter=Depends(adapter_auth)):
    from .iot_ingestion import ingest_event
    if body.get("device_id") not in request.app.state.settings.adapter_allowed_device_ids:
        raise DomainError("adapter_scope_denied", "Adapter is not authorized for this identity", 403)
    row, created = ingest_event(db, body)
    db.commit()
    return envelope({"durable": True, "event_id": row.id, "device_id": row.device_id, "boot_id": row.boot_id,
        "sequence": row.sequence, "status": "stored" if created else "duplicate", "server_received_at": iso(row.server_received_at)})


@router.post("/ingest/channel-acks", tags=["ingestion"], response_model=Envelope[IoTAckReceipt], openapi_extra=contract_request("switch-ack"))
def channel_ack(body: dict, request: Request, db: DB, adapter=Depends(adapter_auth)):
    from .iot_ingestion import ingest_switch_ack
    if body.get("device_id") not in request.app.state.settings.adapter_allowed_device_ids:
        raise DomainError("adapter_scope_denied", "Adapter is not authorized for this identity", 403)
    row, created = ingest_switch_ack(db, body)
    db.commit()
    return envelope({"durable": True, "device_id": row.device_id, "id": row.command_id, "seq": row.sequence,
        "channel": row.channel_number, "status": "stored" if created else "duplicate", "physical_verification": False})


def timeline_events(db, space, start, end):
    results = []
    samples = db.scalars(select(ChannelObservation).where(ChannelObservation.space_id == space.id,
        ChannelObservation.observed_at >= start, ChannelObservation.observed_at < end).order_by(ChannelObservation.observed_at, ChannelObservation.id).limit(10001)).all()
    if len(samples) > 10000:
        raise DomainError("timeline_too_dense", "Reduce the interval to show at most 10,000 observation events", 422)
    for row in samples:
        results.append({"id": f"observation-{row.id}", "at": row.observed_at, "type": "observation", "device_id": row.device_id,
            "channel_id": row.channel_id, "command_id": None, "status": row.quality,
            "actuator_reported_on": row.value.get("actuator_reported_on") if row.quality == "good" else None,
            "verification_kind": "actuator_reported_only" if "actuator_reported_on" in row.value else "independent_feedback" if "output_present" in row.value else None,
            "requested_on": row.value.get("desired_on"), "output_present": row.value.get("output_present") if row.quality == "good" else None,
            "source_mode": row.source_mode, "description": "Observed channel evidence; historical binding and freshness apply"})
    bindings = list(db.scalars(select(Binding).where(Binding.space_id == space.id, Binding.valid_from < end)))
    device_ids = {b.device_id for b in bindings}
    commands = db.scalars(select(Command).where(Command.device_id.in_(device_ids), Command.issued_at < end,
        Command.expires_at >= start)).all()
    for command in commands:
        if not any(b.device_id == command.device_id and b.valid_from <= command.issued_at and (b.valid_to is None or command.issued_at < b.valid_to) for b in bindings):
            continue
        desired = command.history[0].get("evidence", {}).get("desired_on") if command.history else None
        for i, transition in enumerate(command.history):
            at = datetime.fromisoformat(transition["at"].replace("Z", "+00:00"))
            if start <= at < end:
                evidence = transition.get("evidence", {})
                results.append({"id": f"{command.id}-{i}", "at": at, "type": "command", "device_id": command.device_id,
                    "channel_id": command.channel_id, "command_id": command.id,
                    "actuator_reported_on": evidence.get("actuator_reported_on"), "verification_kind": "actuator_reported_only" if command.product_family == "SWITCH" else "independent_feedback", "status": transition["status"], "requested_on": desired,
                    "output_present": evidence.get("output_present"), "source_mode": command.source_mode, "description": transition["reason"]})
    return sorted(results, key=lambda e: (e["at"], e["id"]))
