"""One bounded, revisioned anomaly configuration per room; no arbitrary rule language."""
from sqlalchemy import select
from .models import Space, RoomAnomalyRule, RoomAnomaly
from .classroom_schemas import AnomalyRuleConfig
from .common import DomainError
from .db import utcnow, iso
from .classrooms import audit_room


def rule_for(db, space):
    row=db.get(RoomAnomalyRule,space.id)
    return {"space_id":space.id,"revision":row.revision if row else 0,
        "config":AnomalyRuleConfig(**row.config).model_dump() if row else AnomalyRuleConfig().model_dump(),
        "updated_at":row.updated_at if row else None,"updated_by":row.updated_by if row else None,
        "reason":row.reason if row else "Engineering defaults for review; not calibrated campus conclusions",
        "defaults_are_engineering_assumptions":True}


def patch_rule(db,space,body,actor,now=None):
    now=now or utcnow()
    db.scalar(select(Space.id).where(Space.id==space.id).with_for_update())
    row=db.get(RoomAnomalyRule,space.id)
    revision=row.revision if row else 0
    if body.expected_revision!=revision:
        raise DomainError("rule_revision_conflict","Anomaly rule changed; reload before saving",409,{"current_revision":revision})
    config=rule_for(db,space)["config"] | body.model_dump(exclude_unset=True,exclude={"expected_revision","reason"})
    if row:
        row.revision+=1;row.config=config;row.updated_at=now;row.updated_by=actor;row.reason=body.reason
    else:
        row=RoomAnomalyRule(space_id=space.id,campus_id=space.campus_id,revision=1,config=config,updated_at=now,updated_by=actor,reason=body.reason)
        db.add(row)
    for episode in db.scalars(select(RoomAnomaly).where(RoomAnomaly.space_id==space.id,RoomAnomaly.status!="resolved")):
        episode.status="resolved";episode.resolved_at=now
        episode.notes=[*episode.notes,{"at":iso(now),"by":actor,"action":"rule_superseded","text":f"Configuration revision {row.revision} supersedes this episode; prior evidence and threshold retained"}]
    audit_room(db,actor,"rule_updated",space,"room_anomaly_rule",space.id,{"revision":row.revision,"previous_revision":revision,"config":config,"reason":body.reason})
    db.flush()
    return rule_for(db,space)
