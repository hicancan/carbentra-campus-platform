"""Same application/image, independent bounded projection/evaluation worker role."""
import logging
from .db import utcnow,iso
from .models import State
from .projection import rebuild_one_batch
from .forecast_jobs import evaluate_one
from .worker_health import publish


def analysis_tick(factory,settings):
    hours=rebuild_one_batch(factory)
    evaluated=evaluate_one(factory,settings)
    from .room_anomalies import evaluate_batch
    evaluate_batch(factory)
    now=utcnow()
    with factory() as db:
        state=db.get(State,'analysis_worker')
        value={'status':'running','role':'analysis','last_tick_at':iso(now),'last_tick_epoch':now.timestamp(),
            'hours_processed':hours,'evaluation_completed':evaluated,'raw_scan_in_http':False,'physical_actions':False}
        if state:state.value=value
        else:db.add(State(key='analysis_worker',value=value))
        db.commit()
    publish('analysis',now.timestamp())
    return hours,evaluated


def run_analysis(factory,settings,stop):
    # Lower only this independent analysis process's CPU priority on Linux.
    # Database transactions remain bounded and never hold Device locks.
    import os
    try:os.nice(5)
    except (AttributeError,OSError):pass
    while not stop.is_set():
        busy=False
        try:
            hours,evaluated=analysis_tick(factory,settings)
            busy=bool(hours or evaluated)
        except Exception as exc:
            logging.getLogger(__name__).error('Analysis tick failed (%s)',type(exc).__name__)
        # A fixed one-second delay per day/device batch would add ~18minutes to
        # the1088-batch cold fixture. Yield briefly while work exists, then idle.
        stop.wait(min(.05,settings.analysis_interval_seconds) if busy else settings.analysis_interval_seconds)
