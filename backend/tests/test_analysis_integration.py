"""Synthetic HTTP → durable projection → analysis → cached forecast integration."""
from datetime import timedelta
from sqlalchemy import select,insert,delete,func
from app.db import utcnow
from app.models import Device,Binding,Telemetry,ForecastDirtyHour,ForecastHourRevision,ForecastRun,ForecastProjectionState
from app.projection import hour,queue_history,rebuild_one_batch,pending_count
from app.forecast_jobs import evaluate_one


def test_background_projection_produces_a_schema_valid_cached_forecast(app,admin):
    application,_=app;client,_=admin;now=utcnow();end=hour(now)
    with application.state.session_factory() as db:
        db.execute(delete(ForecastDirtyHour));db.execute(delete(Telemetry))
        for device in db.scalars(select(Device)).all():
            binding=db.scalar(select(Binding).where(Binding.device_id==device.id));binding.valid_from=end-timedelta(days=20)
            rows=[]
            for index in range(14*48+1):
                at=end-timedelta(minutes=30*(14*48-index));power=1000.0+50*(at.hour%6)
                rows.append(dict(device_id=device.id,boot_epoch='a'*32,sample_seq=str(index),observed_at=at,received_at=at,
                    payload_hash='synthetic-fixture',raw_payload={'valid':True,'calibrated':True},time_source='simulated',time_uncertainty_ms=0.0,
                    active_power_w=power,quality='good',quality_flags=[],source_mode='SIMULATED',source_version='analysis-test-v1',
                    campus_id=device.campus_id,building_id=device.building_id,circuit_id=device.circuit_id,binding_id=binding.id))
            db.execute(insert(Telemetry),rows)
            latest=db.scalar(select(Telemetry).where(Telemetry.device_id==device.id).order_by(Telemetry.observed_at.desc()).limit(1))
            device.latest_telemetry_id=latest.id;device.last_seen_at=latest.received_at
        db.flush();db.commit()
    first=client.get('/api/v1/forecasts');assert first.status_code==200,first.text
    assert first.json()['data']['evaluation']['status']=='queued'
    with application.state.session_factory() as db:
        assert all(not state.history_initialized for state in db.scalars(select(ForecastProjectionState)))
    now=utcnow()
    assert not evaluate_one(application.state.session_factory,application.state.settings,now=now)
    with application.state.session_factory() as db:
        assert all(state.history_initialized for state in db.scalars(select(ForecastProjectionState)))
        assert pending_count(db,['SIM-A','SIM-VIRTUAL'],now)>600
    batches=0
    while True:
        with application.state.session_factory() as db:
            remaining=pending_count(db,['SIM-A','SIM-VIRTUAL'],now)
        if not remaining:break
        assert batches<40,'Bounded fixture projection failed to drain'
        assert rebuild_one_batch(application.state.session_factory,now)>0;batches+=1
    assert evaluate_one(application.state.session_factory,application.state.settings,now=now+timedelta(seconds=6))
    ready=client.get('/api/v1/forecasts');assert ready.status_code==200,ready.text
    result=ready.json()['data']
    assert result['evaluation']['status']=='ready' and result['evaluation']['cached']
    assert result['model']['trained'] and all(point['predicted_kw'] is not None for point in result['points'])
    assert result['provenance']['reader']=='persistent_hour_revisions'
    with application.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(ForecastHourRevision))>600
        assert db.scalar(select(func.count()).select_from(ForecastRun))==1
