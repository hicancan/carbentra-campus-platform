"""Durable bounded dirty-hour work for rebuildable forecast evidence.

Ingestion only marks work in its own transaction. Expensive interval reconstruction
runs in the analysis role; it never shares a control tick or takes a Device row lock.
"""
from datetime import timedelta
from sqlalchemy import select,func,case,delete,or_
from .db import utcnow
from .models import Device,Telemetry,ForecastDirtyHour,ForecastHourRevision,ForecastProjectionState
from .common import DomainError,uid

HOUR=timedelta(hours=1)
HISTORY_DAYS=21
MAX_BATCH_HOURS=24


def hour(value):
    return value.replace(minute=0,second=0,microsecond=0)


def _upsert_dirty(db,rows):
    if not rows:
        return
    if db.bind.dialect.name=='postgresql':
        from sqlalchemy.dialects.postgresql import insert
        maximum,minimum=func.greatest,func.least
    elif db.bind.dialect.name=='sqlite':
        from sqlalchemy.dialects.sqlite import insert
        maximum,minimum=func.max,func.min
    else:
        raise DomainError('projection_dialect_unsupported','Hourly projection requires PostgreSQL or explicit SQLite test/development storage',503)
    table=ForecastDirtyHour.__table__
    for offset in range(0,len(rows),500):
        query=insert(table).values(rows[offset:offset+500]);incoming=query.excluded
        query=query.on_conflict_do_update(index_elements=['device_id','hour_end'],set_={
            'source_watermark':maximum(table.c.source_watermark,incoming.source_watermark),
            'not_before':minimum(table.c.not_before,incoming.not_before),
            'attempts':case((incoming.source_watermark>table.c.source_watermark,0),else_=table.c.attempts),
            'last_error':case((incoming.source_watermark>table.c.source_watermark,None),else_=table.c.last_error)})
        db.execute(query)


def _state(db,device):
    state=db.get(ForecastProjectionState,device.id)
    if state is None:
        state=next((x for x in db.new if isinstance(x,ForecastProjectionState) and x.device_id==device.id),None)
    if state is None:
        state=ForecastProjectionState(device_id=device.id,campus_id=device.campus_id,status='queued',source_watermark=0,closed_revision_id=0)
        db.add(state)
    elif state.campus_id!=device.campus_id:
        state.campus_id=device.campus_id
    return state


def mark_observation(db,device,sample):
    if 'metering' not in device.capabilities:
        return
    now=utcnow();at=sample.observed_at
    # Out-of-window facts remain durable raw evidence. They cannot affect this
    # explicitly bounded forecasting window and do not create unbounded queue keys.
    if at<now-timedelta(days=HISTORY_DAYS+1) or at>now+timedelta(seconds=5):
        return
    cadence=1800 if sample.source_mode=='SIMULATED' else 30
    containing=hour(at)+HOUR
    targets={containing}
    # Only a neighboring hour reachable by a valid interval can be affected.
    if (at-hour(at)).total_seconds()<=cadence:
        targets.add(containing-HOUR)
    if (containing-at).total_seconds()<=cadence:
        targets.add(containing+HOUR)
    rows=[]
    for end in sorted(targets):
        due=end+timedelta(seconds=cadence)
        if at>=end and sample.received_at>=end:
            due=min(due,sample.received_at)
        rows.append({'device_id':device.id,'hour_end':end,'source_watermark':sample.id,'queued_at':now,'not_before':due,'attempts':0,'last_error':None})
    _upsert_dirty(db,rows)
    state=_state(db,device)
    if any(row['not_before']<=now for row in rows):
        state.status='queued'


def queue_history(db,device_ids=None,start=None,end=None,now=None):
    """Explicit cold rebuild/seed hook. Never called from an HTTP request."""
    now=now or utcnow()
    if any(value is not None and value.tzinfo is None for value in (start,end,now)):
        raise DomainError('invalid_projection_period','Projection timestamps require a UTC offset',422)
    end=min(end or now,now);start=max(start or end-timedelta(days=HISTORY_DAYS),end-timedelta(days=HISTORY_DAYS))
    if start>=end:
        raise DomainError('invalid_projection_period','Projection history period must be positive',422)
    if device_ids is None:
        from .accounting import selected_devices
        device_ids=[d.id for d in selected_devices(db,start=now,end=now)]
    device_ids=list(set(device_ids))
    if len(device_ids)>2000:
        raise DomainError('projection_device_budget','Queue at most 2000 metering devices per operation',422)
    devices={d.id:d for d in db.scalars(select(Device).where(Device.id.in_(device_ids)))}
    if len(devices)!=len(device_ids):
        raise DomainError('unknown_device','One or more projection devices are unavailable',404)
    rows=db.execute(select(Telemetry.device_id,func.min(Telemetry.observed_at),func.max(Telemetry.observed_at),func.max(Telemetry.id))
        .where(Telemetry.device_id.in_(device_ids),Telemetry.observed_at>=start,Telemetry.observed_at<=end,Telemetry.received_at<=now).group_by(Telemetry.device_id)).all()
    queued=0;present=set()
    for ident,first,last,watermark in rows:
        device=devices.get(ident)
        if device is None or 'metering' not in device.capabilities:
            continue
        present.add(ident);state=_state(db,device);state.status='queued';state.history_initialized=True
        cadence=1800 if device.source_mode=='SIMULATED' else 30
        cursor=hour(first)+HOUR;finish=hour(last)+HOUR;items=[]
        while cursor<=finish:
            due=cursor+timedelta(seconds=cadence)
            if last>=cursor:
                due=min(due,now)
            items.append({'device_id':ident,'hour_end':cursor,'source_watermark':int(watermark),'queued_at':now,'not_before':due,'attempts':0,'last_error':None})
            cursor+=HOUR
        _upsert_dirty(db,items);queued+=len(items)
    for ident,device in devices.items():
        if ident not in present:
            state=_state(db,device);state.status='ready';state.history_initialized=True
    db.flush()
    return {'devices':len(devices),'hours_marked':queued,'window_start':start.isoformat(),'window_end':end.isoformat()}


def pending_count(db,device_ids,now=None,include_failed=False):
    now=now or utcnow()
    query=select(func.count()).select_from(ForecastDirtyHour).where(ForecastDirtyHour.device_id.in_(device_ids),ForecastDirtyHour.not_before<=now,ForecastDirtyHour.hour_end>=hour(now)-timedelta(days=HISTORY_DAYS))
    if not include_failed:
        query=query.where(ForecastDirtyHour.attempts<3)
    return int(db.scalar(query) or 0)


def rebuild_one_batch(factory,now=None):
    from .forecasting import rebuild_forecast_hours
    now=now or utcnow();lease=uid('projection_lease')
    eligible=lambda: (ForecastDirtyHour.not_before<=now,ForecastDirtyHour.attempts<3,
        ForecastDirtyHour.hour_end>=hour(now)-timedelta(days=HISTORY_DAYS),
        or_(ForecastDirtyHour.lease_id.is_(None),ForecastDirtyHour.lease_expires_at<=now))
    with factory() as db:
        first=db.scalar(select(ForecastDirtyHour).where(*eligible()).order_by(ForecastDirtyHour.hour_end,ForecastDirtyHour.device_id).with_for_update(skip_locked=True).limit(1))
        if first is None:
            return 0
        jobs=list(db.scalars(select(ForecastDirtyHour).where(ForecastDirtyHour.device_id==first.device_id,
            ForecastDirtyHour.hour_end>=first.hour_end,ForecastDirtyHour.hour_end<first.hour_end+MAX_BATCH_HOURS*HOUR,*eligible())
            .order_by(ForecastDirtyHour.hour_end).with_for_update(skip_locked=True).limit(MAX_BATCH_HOURS)))
        ident=first.device_id;claimed={job.hour_end:job.source_watermark for job in jobs}
        for job in jobs:
            job.lease_id=lease;job.lease_expires_at=now+timedelta(seconds=180);job.attempts+=1
        db.commit()
    # No dirty or Device row lock is held during expensive reconstruction. Fresh
    # ingest can durably coalesce a newer watermark while this bounded lease runs.
    try:
        with factory() as db:
            revisions=rebuild_forecast_hours(db,ident,list(claimed),as_of=now)
            db.flush()
            jobs=list(db.scalars(select(ForecastDirtyHour).where(ForecastDirtyHour.device_id==ident,
                ForecastDirtyHour.hour_end.in_(claimed),ForecastDirtyHour.lease_id==lease)
                .order_by(ForecastDirtyHour.hour_end).with_for_update()))
            if len(jobs) != len(claimed):
                # A replacement worker owns any lost hour. Publish this bounded
                # batch atomically or not at all; do not append revisions for
                # work whose lease changed during reconstruction.
                db.rollback();return len(claimed)
            state=db.scalar(select(ForecastProjectionState).where(ForecastProjectionState.device_id==ident).with_for_update().execution_options(populate_existing=True))
            device=db.get(Device,ident)
            if state is None and device:
                state=_state(db,device)
            if state:
                state.source_watermark=max(state.source_watermark or 0,max(claimed.values(),default=0))
                state.closed_revision_id=max(state.closed_revision_id or 0,max((row.id for row in revisions),default=0))
                state.last_projected_hour=max(list(claimed)+([state.last_projected_hour] if state.last_projected_hour else []))
                state.status='ready';state.updated_at=now
            for job in jobs:
                if job.source_watermark==claimed[job.hour_end]:
                    db.delete(job)
                else:
                    # New evidence arrived after the claim; retain it for another
                    # revision instead of erasing the new work or calling it fresh.
                    job.lease_id=None;job.lease_expires_at=None;job.attempts=0
            db.commit()
    except Exception as exc:
        with factory() as db:
            jobs=list(db.scalars(select(ForecastDirtyHour).where(ForecastDirtyHour.device_id==ident,
                ForecastDirtyHour.hour_end.in_(claimed),ForecastDirtyHour.lease_id==lease).with_for_update()))
            for job in jobs:
                job.last_error='projection_rebuild_failed';job.not_before=now+timedelta(seconds=min(60,max(1,job.attempts)*5))
                job.lease_id=None;job.lease_expires_at=None
            state=db.get(ForecastProjectionState,ident)
            if state:state.status='failed'
            db.commit()
        import logging
        logging.getLogger(__name__).error('Projection batch failed (%s)',type(exc).__name__)
    return len(claimed)
