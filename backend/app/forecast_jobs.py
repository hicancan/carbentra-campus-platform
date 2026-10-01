"""Scoped, deduplicated forecast evaluation outside request/control execution.

The result cache is derived and bounded. Raw observations and closed-hour revisions
remain truth; a cached result keeps its original generated/training timestamps.
"""
import copy
from datetime import timedelta
from sqlalchemy import select,func,text,or_,update
from .accounting import selected_devices
from .common import DomainError,payload_hash,uid,require_entity
from .db import utcnow,iso
from .models import Campus,Building,Device,Telemetry,User,ForecastRun,ForecastProjectionState,ForecastDirtyHour,Event
from .projection import hour,pending_count,queue_history

LEASE_SECONDS=180
MAX_ATTEMPTS=3


def _scope(db,campus_id,building_id):
    if campus_id:
        require_entity(db,Campus,campus_id)
    if building_id:
        building=require_entity(db,Building,building_id)
        if campus_id and building.campus_id!=campus_id:
            raise DomainError('scope_mismatch','Building is not within the requested campus',422)


def inputs(db,campus_id,building_id,now):
    from .forecasting import VERSION,forecast_head_evidence
    _scope(db,campus_id,building_id)
    devices=selected_devices(db,campus_id,building_id,start=now,end=now)
    ids=[device.id for device in devices]
    binding_ids={device.id:sorted(device.eligible_binding_ids) for device in devices}
    states={row.device_id:row for row in db.scalars(select(ForecastProjectionState).where(ForecastProjectionState.device_id.in_(ids)))}
    registry=list(db.scalars(select(Device).where(Device.id.in_(ids))))
    latest_valid,_=forecast_head_evidence(db,devices,now,campus_id,building_id)
    identity=[]
    for device in registry:
        available=device.id in latest_valid
        identity.append((device.id,device.campus_id,device.building_id,device.circuit_id,device.source_mode,binding_ids.get(device.id,[]),
            states[device.id].closed_revision_id if device.id in states else 0,available))
    zones=[(row.id,row.timezone) for row in db.scalars(select(Campus).where(Campus.id.in_({d.campus_id for d in registry})))]
    revision=payload_hash({'model':VERSION,'origin_hour':iso(hour(now)),'devices':sorted(identity),'calendar':sorted(zones)})
    return devices,revision,pending_count(db,ids,now,include_failed=True),[ident for ident in ids if ident not in states or not states[ident].history_initialized]


def _allowed(user,scope):
    return bool(user and user.enabled and user.role in {'admin','operator','analyst','viewer'} and
        (user.campus_ids is None or (scope is not None and set(scope).issubset(set(user.campus_ids)))))


def _evaluation(run,status,revision,pending,cached):
    return {'id':run.id if run else None,'status':status,'worker_status':run.status if run else 'ready',
        'requested_at':iso(run.requested_at) if run else None,'started_at':iso(run.started_at) if run else None,
        'completed_at':iso(run.completed_at) if run else None,'input_revision':revision,
        'result_input_revision':run.result_input_revision if run else None,'projection_pending_hours':pending,
        'retry_after_seconds':5 if status in {'queued','running','stale'} else 60,'error_code':run.error_code if run else None,'cached':cached}


def cached_forecast(db,settings,user,campus_id=None,building_id=None,horizon_hours=24,retry=False,now=None):
    from .forecasting import VERSION,forecast_template
    now=now or utcnow()
    devices,revision,pending,missing=inputs(db,campus_id,building_id,now)
    if not devices:
        result=forecast_template(devices,campus_id,building_id,horizon_hours,now)
        result['warnings'].append('No eligible metering devices in this scope')
        result['evaluation']=_evaluation(None,'ready',revision,0,False)
        return result
    scope=None if user.campus_ids is None else sorted(set(user.campus_ids))
    parameters={'campus_id':campus_id,'building_id':building_id,'horizon_hours':horizon_hours}
    key=payload_hash({'parameters':parameters,'authorized_campus_ids':scope,'model_version':VERSION})
    run=db.scalar(select(ForecastRun).where(ForecastRun.cache_key==key))
    # These comparisons prevent a malformed/imported cache row from broadening its key.
    if run and (run.authorized_campus_ids!=scope or run.parameters!=parameters or run.model_version!=VERSION):
        raise DomainError('forecast_cache_scope_conflict','Cached evaluation scope does not match the request',409)
    needs_write=(run is None or (run.status=='ready' and (run.result_input_revision!=revision or pending or missing))
        or (run.status=='failed' and (retry or run.input_revision!=revision))
        or (run.status=='running' and run.lease_expires_at and run.lease_expires_at<=now))
    if needs_write:
        # GET cache population is an internal derived operation, not a control action.
        # End the read snapshot before SQLite's explicit bounded writer transaction.
        db.commit()
        if db.bind.dialect.name=='sqlite':
            db.connection(execution_options={'sqlite_write':True})
        elif db.bind.dialect.name=='postgresql':
            db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':int(key[:16],16)&((1<<63)-1)})
        run=db.scalar(select(ForecastRun).where(ForecastRun.cache_key==key).with_for_update().execution_options(populate_existing=True))
        if run is None or run.status not in {'queued','running'}:
            # Per-key locks deduplicate but cannot enforce a cross-key quota. A
            # short shared reservation lock serializes only new pending admission.
            if db.bind.dialect.name=='postgresql':
                db.execute(text('SELECT pg_advisory_xact_lock(48392718)'))
            queued=db.scalar(select(func.count()).select_from(ForecastRun).where(ForecastRun.status.in_(['queued','running'])))
            personal=db.scalar(select(func.count()).select_from(ForecastRun).where(ForecastRun.requested_by==user.id,ForecastRun.status.in_(['queued','running'])))
            total=db.scalar(select(func.count()).select_from(ForecastRun))
            if queued>=settings.forecast_max_pending or personal>=16 or (run is None and total>=settings.forecast_max_cached_runs):
                raise DomainError('forecast_queue_full','Bounded analysis capacity is busy; retry an existing scope or wait',429)
        if run is None:
            resolved_campus=campus_id or (db.get(Building,building_id).campus_id if building_id else scope[0] if scope and len(scope)==1 else None)
            run=ForecastRun(id=uid('forecast'),cache_key=key,campus_id=resolved_campus,authorized_campus_ids=scope,requested_by=user.id,
                parameters=parameters,model_version=VERSION,input_revision=revision,status='queued',requested_at=now,not_before=now,attempts=0)
            db.add(run)
        elif run.status!='running' or (run.lease_expires_at and run.lease_expires_at<=now):
            if run.status=='running' and run.attempts>=MAX_ATTEMPTS:
                run.status='failed';run.error_code='analysis_lease_exhausted'
            else:
                if retry or run.input_revision!=revision or run.status=='ready':
                    run.attempts=0
                if retry and run.status=='failed':
                    db.execute(update(ForecastDirtyHour).where(ForecastDirtyHour.device_id.in_([device.id for device in devices]),
                        ForecastDirtyHour.hour_end>=hour(now)-timedelta(days=21),ForecastDirtyHour.attempts>=MAX_ATTEMPTS,
                        or_(ForecastDirtyHour.lease_id.is_(None),ForecastDirtyHour.lease_expires_at<=now))
                        .values(attempts=0,last_error=None,not_before=now,lease_id=None,lease_expires_at=None))
                run.status='queued';run.input_revision=revision;run.requested_by=user.id;run.requested_at=now;run.not_before=now
                run.lease_id=None;run.lease_expires_at=None;run.error_code=None
        db.commit()
    cached=run.result is not None
    if cached:
        result=copy.deepcopy(run.result)
        status='failed' if run.status=='failed' else 'stale' if run.result_input_revision!=revision or pending or missing or run.status in {'queued','running'} else 'ready'
        if status=='stale':
            result['warnings'].append('Stored forecast is stale while a scoped background refresh is pending; generated/training timestamps remain unchanged')
    else:
        result=forecast_template(devices,campus_id,building_id,horizon_hours,now)
        status=run.status
        result['warnings'].append('Forecast evaluation is '+status+' in the analysis worker; null predictions are unavailable, never zero')
    if run.status=='failed':
        result['warnings'].append('Background evaluation failed; use the explicit refresh action after resolving the reported error')
    result['provenance']['cache']='persisted_scope_bound_evaluation'
    result['evaluation']=_evaluation(run,status,revision,pending,cached)
    return result


def evaluate_one(factory,settings,now=None):
    """Claim a bounded lease, compute separately, then publish only for that lease."""
    from .forecasting import VERSION,forecast
    from .responses import ForecastResponse
    now=now or utcnow();claimed=None
    with factory() as db:
        candidates=list(db.scalars(select(ForecastRun.id).where(or_((ForecastRun.status=='queued')&(ForecastRun.not_before<=now),
            (ForecastRun.status=='running')&(ForecastRun.lease_expires_at<=now))).order_by(ForecastRun.requested_at).limit(8)))
    for candidate in candidates:
        bootstrap_ids=[]
        # A fresh identity map for every authorization context. Reusing a Session
        # across users could make db.get return an object loaded under another ACL.
        with factory() as db:
            run=db.scalar(select(ForecastRun).where(ForecastRun.id==candidate).with_for_update(skip_locked=True))
            if not run or run.status not in {'queued','running'} or (run.status=='running' and run.lease_expires_at>now):
                continue
            user=db.get(User,run.requested_by)
            if not _allowed(user,run.authorized_campus_ids):
                run.status='failed';run.error_code='requester_scope_revoked'
            elif run.model_version!=VERSION:
                run.status='failed';run.error_code='forecast_model_version_changed'
            elif run.attempts>=MAX_ATTEMPTS:
                run.status='failed';run.error_code='analysis_retry_exhausted'
            else:
                db.info['campus_ids']=run.authorized_campus_ids;db.info['actor']=user.id
                try:
                    devices,revision,pending,missing=inputs(db,run.parameters['campus_id'],run.parameters['building_id'],now)
                    if missing:
                        bootstrap_ids=missing
                        run.not_before=now+timedelta(seconds=5)
                    else:
                        ids=[device.id for device in devices]
                        failed=db.scalar(select(func.count()).select_from(ForecastDirtyHour).where(ForecastDirtyHour.device_id.in_(ids),ForecastDirtyHour.attempts>=3,ForecastDirtyHour.hour_end>=hour(now)-timedelta(days=21),
                            or_(ForecastDirtyHour.lease_id.is_(None),ForecastDirtyHour.lease_expires_at<=now)))
                        if failed:
                            run.status='failed';run.error_code='projection_rebuild_failed'
                        elif pending:
                            run.not_before=now+timedelta(seconds=5)
                        else:
                            if run.result is not None and run.result_input_revision==revision:
                                run.status='ready';run.lease_id=None;run.lease_expires_at=None
                            else:
                                run.status='running';run.started_at=now;run.attempts+=1;run.lease_id=uid('evaluation_lease');run.lease_expires_at=now+timedelta(seconds=LEASE_SECONDS)
                                run.input_revision=revision;run.error_code=None
                                claimed=(run.id,run.lease_id,run.requested_by,run.authorized_campus_ids,dict(run.parameters),revision)
                except DomainError as exc:
                    run.status='failed';run.error_code=exc.code
            db.commit()
        # Derived evidence is infrastructure-owned and placement-partitioned. The
        # selected IDs were authorized above; backfill must see their full history
        # rather than setting a global initialized flag from one user's subset.
        # Per-device commits avoid holding cross-device queue/state locks behind
        # a large ingestion batch in the opposite device order.
        for device_id in sorted(bootstrap_ids):
            with factory() as internal:
                queue_history(internal,[device_id],now=now)
                internal.commit()
        if claimed:
            break
    if not claimed:
        return False
    ident,lease,actor,scope,parameters,revision=claimed
    result,error=None,None
    try:
        with factory() as db:
            if not _allowed(db.get(User,actor),scope):
                raise DomainError('requester_scope_revoked','Requester authorization changed',403)
            db.info['campus_ids']=scope;db.info['actor']=actor
            result=forecast(db,**parameters,now=now,reader='projection')
            result=ForecastResponse.model_validate(result).model_dump(mode='json',exclude_unset=True)
    except Exception as exc:
        error=exc.code if isinstance(exc,DomainError) else 'forecast_evaluation_failed'
        import logging
        logging.getLogger(__name__).error('Background forecast failed (%s)',type(exc).__name__)
    with factory() as db:
        run=db.scalar(select(ForecastRun).where(ForecastRun.id==ident).with_for_update())
        if not run or run.lease_id!=lease or run.status!='running':
            return False
        if not _allowed(db.get(User,actor),scope):
            error='requester_scope_revoked';result=None
        run.lease_id=None;run.lease_expires_at=None
        if error:
            run.error_code=error;run.status='queued' if run.attempts<MAX_ATTEMPTS and error!='requester_scope_revoked' else 'failed'
        else:
            run.result=result;run.result_input_revision=revision;run.status='ready';run.completed_at=utcnow();run.error_code=None
            db.add(Event(type='forecast.ready',entity_id=run.id,campus_id=run.campus_id))
        db.commit()
    return True
