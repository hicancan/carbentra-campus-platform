"""Small deterministic boundaries for background forecast scheduling."""
from datetime import timedelta

from sqlalchemy import delete, select

from test_resource_scope import scoped, value


def test_pending_broad_scopes_do_not_starve_a_ready_narrow_scope(scoped,monkeypatch):
    from app import forecasting
    from app.accounting import selected_devices
    from app.db import utcnow
    from app.forecast_jobs import evaluate_one
    from app.models import ForecastDirtyHour, ForecastProjectionState
    from app.projection import hour
    application,client,_,records=scoped
    with application.state.session_factory() as db:
        db.execute(delete(ForecastDirtyHour))
        for state in db.scalars(select(ForecastProjectionState)):
            state.history_initialized=True
        now=utcnow()
        db.add(ForecastDirtyHour(device_id=records['B']['device'],hour_end=hour(now)-timedelta(hours=1),
            source_watermark=1,not_before=now-timedelta(seconds=1),attempts=0))
        db.commit()
    # Eight broad requests are legitimately waiting for B's projection. A is
    # already ready and must not wait forever behind the same scan prefix.
    for horizon in range(1,9):
        result=value(client.get('/api/v1/forecasts',params={'horizon_hours':horizon}))
        assert result['evaluation']['status']=='queued'
    parameters={'building_id':records['A']['building'],'horizon_hours':24}
    narrow=value(client.get('/api/v1/forecasts',params=parameters))
    assert narrow['evaluation']['status']=='queued'
    def small_result(db,campus_id=None,building_id=None,horizon_hours=24,now=None,reader=None):
        assert reader=='projection'
        return forecasting.forecast_template(selected_devices(db,campus_id,building_id,start=now,end=now),
            campus_id,building_id,horizon_hours,now)
    monkeypatch.setattr(forecasting,'forecast',small_result)
    # Bounded retries permit a fair scan/backoff implementation without requiring
    # one particular query ordering or a full unbounded queue scan.
    for _ in range(3):
        evaluate_one(application.state.session_factory,application.state.settings)
    ready=value(client.get('/api/v1/forecasts',params=parameters))
    assert ready['evaluation']['status']=='ready','A ready campus scope starved behind repeatedly selected pending broad jobs'
