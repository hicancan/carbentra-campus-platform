"""Fast scoped request/cache boundary with deterministic analysis-worker fixtures."""
import copy
from datetime import timedelta
from sqlalchemy import select,func,delete
from app.db import utcnow
from app.models import ForecastRun,ForecastDirtyHour,ForecastProjectionState,Device,Telemetry,User
from app.forecast_jobs import evaluate_one,inputs
from app import forecasting


def clear_work(application):
    with application.state.session_factory() as db:
        db.execute(delete(ForecastDirtyHour))
        for state in db.scalars(select(ForecastProjectionState)):state.history_initialized=True
        db.commit()


def fake_forecast(db,campus_id=None,building_id=None,horizon_hours=24,now=None,reader=None):
    assert reader=='projection'
    from app.accounting import selected_devices
    result=forecasting.forecast_template(selected_devices(db,start=now,end=now),campus_id,building_id,horizon_hours,now)
    result['warnings'].append('Synthetic queue test result; no trained-model claim')
    return result


def test_first_get_and_repeated_requests_do_not_read_raw_history_or_train(app,admin,monkeypatch):
    application,_=app;client,_=admin
    def forbidden(*args,**kwargs):raise AssertionError('Training/raw history must never run in HTTP')
    monkeypatch.setattr(forecasting,'forecast',forbidden)
    monkeypatch.setattr(forecasting,'_read_hourly_sql',forbidden)
    first=client.get('/api/v1/forecasts');second=client.get('/api/v1/forecasts')
    assert first.status_code==second.status_code==200
    first,second=first.json()['data'],second.json()['data']
    assert first['evaluation']['status']=='queued'
    assert first['evaluation']['id']==second['evaluation']['id']
    assert first['evaluation']['requested_at']==second['evaluation']['requested_at']
    assert all(point['predicted_kw'] is None for point in first['points'])
    with application.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(ForecastRun))==1


def test_worker_publishes_persisted_result_and_closed_revision_makes_it_explicitly_stale(app,admin,monkeypatch):
    application,_=app;client,_=admin;clear_work(application)
    monkeypatch.setattr(forecasting,'forecast',fake_forecast)
    queued=client.get('/api/v1/forecasts').json()['data']
    assert evaluate_one(application.state.session_factory,application.state.settings)
    ready=client.get('/api/v1/forecasts').json()['data']
    assert ready['evaluation']['status']=='ready' and ready['evaluation']['cached']
    generated=ready['generated_at']
    with application.state.session_factory() as db:
        state=db.get(ForecastProjectionState,'SIM-A');state.closed_revision_id+=1;db.commit()
    stale=client.get('/api/v1/forecasts').json()['data']
    assert stale['evaluation']['status']=='stale' and stale['evaluation']['worker_status']=='queued'
    assert stale['generated_at']==generated
    assert stale['evaluation']['input_revision']!=stale['evaluation']['result_input_revision']
    assert evaluate_one(application.state.session_factory,application.state.settings)
    assert client.get('/api/v1/forecasts').json()['data']['evaluation']['status']=='ready'


def test_open_sample_identity_is_not_an_ever_changing_training_revision(app,admin):
    application,_=app;clear_work(application)
    with application.state.session_factory() as db:
        now=utcnow()
        _,before,_,_=inputs(db,None,None,now)
        device=db.get(Device,'SIM-A');sample=db.get(Telemetry,device.latest_telemetry_id)
        sample.active_power_w+=15;sample.sample_seq='20';sample.received_at=now
        device.last_seen_at=now;db.commit()
        _,after,_,_=inputs(db,None,None,now)
        assert before==after


def test_failed_evaluation_is_bounded_redacted_and_explicitly_retryable(app,admin,monkeypatch,caplog):
    application,_=app;client,headers=admin;clear_work(application)
    def failure(*args,**kwargs):raise RuntimeError('SYNTHETIC_SECRET_NOT_FOR_LOGS')
    monkeypatch.setattr(forecasting,'forecast',failure)
    client.get('/api/v1/forecasts')
    for _ in range(3):assert evaluate_one(application.state.session_factory,application.state.settings)
    assert not evaluate_one(application.state.session_factory,application.state.settings)
    result=client.get('/api/v1/forecasts')
    assert result.json()['data']['evaluation']['status']=='failed'
    assert result.json()['data']['evaluation']['error_code']=='forecast_evaluation_failed'
    assert 'SYNTHETIC_SECRET_NOT_FOR_LOGS' not in result.text+caplog.text
    assert client.post('/api/v1/forecasts/refresh',json={}).status_code==403
    response=client.post('/api/v1/forecasts/refresh',headers=headers,json={})
    assert response.status_code==200 and response.json()['data']['evaluation']['status']=='queued'


def test_expired_lease_recovers_after_worker_restart(app,admin,monkeypatch):
    application,_=app;client,_=admin;clear_work(application);monkeypatch.setattr(forecasting,'forecast',fake_forecast)
    ident=client.get('/api/v1/forecasts').json()['data']['evaluation']['id']
    with application.state.session_factory() as db:
        run=db.get(ForecastRun,ident);run.status='running';run.attempts=1;run.lease_id='inert-lost-worker-lease';run.lease_expires_at=utcnow()-timedelta(seconds=1);db.commit()
    assert evaluate_one(application.state.session_factory,application.state.settings)
    result=client.get('/api/v1/forecasts').json()['data']
    assert result['evaluation']['status']=='ready'
    with application.state.session_factory() as db:
        assert db.get(ForecastRun,ident).attempts==2


def test_scope_is_in_cache_key_and_revoked_requester_cannot_compute_old_scope(app,admin,monkeypatch):
    application,_=app;client,headers=admin;clear_work(application);monkeypatch.setattr(forecasting,'forecast',fake_forecast)
    create=client.post('/api/v1/users',headers=headers,json={'username':'forecast-a','display_name':'Synthetic A viewer','role':'viewer','campus_ids':['A'],'password':'fixture-password-long-enough'})
    assert create.status_code==201;ident=create.json()['data']['id']
    global_run=client.get('/api/v1/forecasts').json()['data']['evaluation']['id']
    client.post('/api/v1/auth/login',json={'username':'forecast-a','password':'fixture-password-long-enough'})
    own=client.get('/api/v1/forecasts').json()['data']
    assert own['evaluation']['id']!=global_run
    assert client.get('/api/v1/forecasts?campus_id=B').status_code==404
    with application.state.session_factory() as db:
        db.get(User,ident).campus_ids=['B'];db.commit()
    for _ in range(2):evaluate_one(application.state.session_factory,application.state.settings)
    with application.state.session_factory() as db:
        run=db.get(ForecastRun,own['evaluation']['id'])
        assert run.status=='failed' and run.error_code=='requester_scope_revoked' and run.result is None
    new=client.get('/api/v1/forecasts').json()['data']
    assert new['evaluation']['id'] is None and new['source_mode']=='UNKNOWN'


def test_pending_jobs_are_bounded_per_requester(app,admin):
    application,_=app;client,_=admin
    for horizon in range(1,17):
        assert client.get('/api/v1/forecasts',params={'horizon_hours':horizon}).status_code==200
    response=client.get('/api/v1/forecasts',params={'horizon_hours':17})
    assert response.status_code==429 and response.json()['error']['code']=='forecast_queue_full'
