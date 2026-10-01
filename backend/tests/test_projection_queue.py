from datetime import timedelta
from sqlalchemy import select,func,delete
from app.db import utcnow
from app.models import Device,Telemetry,ForecastDirtyHour,ForecastProjectionState
from app.projection import mark_observation,queue_history,hour


def test_marking_is_idempotent_and_closes_only_hours_with_right_evidence(app):
    application,_=app
    with application.state.session_factory() as db:
        db.execute(delete(ForecastDirtyHour))
        device=db.get(Device,'SIM-A');sample=db.get(Telemetry,device.latest_telemetry_id)
        at=hour(utcnow())-timedelta(hours=1)
        sample.observed_at=sample.received_at=at
        mark_observation(db,device,sample);db.flush()
        first=db.scalar(select(func.count()).select_from(ForecastDirtyHour))
        mark_observation(db,device,sample);db.flush()
        assert db.scalar(select(func.count()).select_from(ForecastDirtyHour))==first
        closed=db.get(ForecastDirtyHour,('SIM-A',at))
        assert closed.not_before==at and closed.source_watermark==sample.id
        assert db.get(ForecastProjectionState,'SIM-A').closed_revision_id==0


def test_out_of_window_raw_evidence_cannot_grow_an_unbounded_work_queue(app):
    application,_=app
    with application.state.session_factory() as db:
        db.execute(delete(ForecastDirtyHour));device=db.get(Device,'SIM-A');sample=db.get(Telemetry,device.latest_telemetry_id)
        for delta in (timedelta(days=-90),timedelta(days=90)):
            sample.observed_at=utcnow()+delta;mark_observation(db,device,sample)
        db.flush()
        assert db.scalar(select(func.count()).select_from(ForecastDirtyHour))==0


def test_cold_queue_uses_observed_history_and_does_not_create_empty_twenty_one_day_ranges(app):
    application,_=app
    with application.state.session_factory() as db:
        db.execute(delete(ForecastDirtyHour))
        result=queue_history(db,['SIM-A']);db.flush()
        assert result['hours_marked']==1
        assert db.scalar(select(func.count()).select_from(ForecastDirtyHour))==1
        assert queue_history(db,['SIM-A'])['hours_marked']==1
        assert db.scalar(select(func.count()).select_from(ForecastDirtyHour))==1


def test_ingestion_during_rebuild_keeps_new_dirty_watermark(app,monkeypatch):
    from app import forecasting
    from app.projection import rebuild_one_batch,_upsert_dirty
    application,_=app;now=utcnow();end=hour(now)
    with application.state.session_factory() as db:
        db.execute(delete(ForecastDirtyHour))
        db.add(ForecastDirtyHour(device_id='SIM-A',hour_end=end,source_watermark=1,queued_at=now,not_before=now))
        db.commit()
    def rebuild(db,ident,hours,as_of):
        # A separate ingest transaction can commit after claim and before publish.
        with application.state.session_factory() as receiving:
            _upsert_dirty(receiving,[{'device_id':ident,'hour_end':end,'source_watermark':2,'queued_at':now,'not_before':now,'attempts':0,'last_error':None}])
            receiving.commit()
        return []
    monkeypatch.setattr(forecasting,'rebuild_forecast_hours',rebuild)
    assert rebuild_one_batch(application.state.session_factory,now)==1
    with application.state.session_factory() as db:
        retained=db.get(ForecastDirtyHour,('SIM-A',end))
        assert retained is not None and retained.source_watermark==2 and retained.lease_id is None
        assert retained.attempts==0


def test_expired_projection_lease_retries_without_losing_work(app,monkeypatch):
    from app import forecasting
    from app.projection import rebuild_one_batch
    application,_=app;now=utcnow();end=hour(now)
    with application.state.session_factory() as db:
        db.execute(delete(ForecastDirtyHour))
        db.add(ForecastDirtyHour(device_id='SIM-A',hour_end=end,source_watermark=1,queued_at=now,not_before=now,
            lease_id='inert-crashed-worker',lease_expires_at=now-timedelta(seconds=1),attempts=1))
        db.commit()
    monkeypatch.setattr(forecasting,'rebuild_forecast_hours',lambda *args,**kwargs:[])
    assert rebuild_one_batch(application.state.session_factory,now)==1
    with application.state.session_factory() as db:
        assert db.get(ForecastDirtyHour,('SIM-A',end)) is None


def test_partial_lease_loss_does_not_publish_any_batch_revision(app,monkeypatch):
    from app import forecasting
    from app.models import ForecastHourRevision
    from app.projection import rebuild_one_batch
    application,_=app;now=utcnow();end=hour(now)
    hours=[end-timedelta(hours=1),end]
    with application.state.session_factory() as db:
        db.execute(delete(ForecastDirtyHour))
        for at in hours:
            db.add(ForecastDirtyHour(device_id='SIM-A',hour_end=at,source_watermark=1,queued_at=now,not_before=now))
        db.commit()
    def rebuild(db,ident,claimed,as_of):
        with application.state.session_factory() as replacement:
            job=replacement.get(ForecastDirtyHour,(ident,end))
            job.lease_id='replacement-worker';job.lease_expires_at=now+timedelta(seconds=180)
            replacement.commit()
        revision=ForecastHourRevision(device_id=ident,campus_id='campus-A',source_mode='SIMULATED',
            scope_key='a'*64,hour_end=end,available_at=now,computed_at=now,source_watermark=1,content_hash='b'*64,data={})
        db.add(revision)
        return [revision]
    monkeypatch.setattr(forecasting,'rebuild_forecast_hours',rebuild)
    assert rebuild_one_batch(application.state.session_factory,now)==2
    with application.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(ForecastHourRevision))==0
        assert db.get(ForecastDirtyHour,('SIM-A',end)).lease_id=='replacement-worker'
        assert db.get(ForecastDirtyHour,('SIM-A',hours[0])) is not None
