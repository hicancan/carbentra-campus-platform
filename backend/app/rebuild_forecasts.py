"""Queue a bounded rebuild of derived forecast hours; raw observations stay untouched."""
import argparse
import json
from datetime import datetime
from .config import Settings
from .db import make_engine,make_session_factory,utcnow
from .accounting import selected_devices
from .projection import queue_history


def aware(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:
        raise argparse.ArgumentTypeError('Use a timestamp with a UTC offset')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue',action='store_true',required=True)
    parser.add_argument('--device-id',action='append',dest='device_ids')
    parser.add_argument('--start',type=aware)
    parser.add_argument('--end',type=aware)
    args=parser.parse_args();settings=Settings(worker_enabled=False)
    engine=make_engine(settings.database_url);factory=make_session_factory(engine);now=utcnow()
    try:
        with factory() as db:
            ids=args.device_ids or [device.id for device in selected_devices(db,start=now,end=now)]
        if len(ids)>2000:
            raise SystemExit('Queue at most 2000 devices per operation')
        results=[]
        for device_id in sorted(set(ids)):
            # One metering identity per transaction: live ingestion batches are not
            # blocked behind a fleet-wide set of derived queue/state row locks.
            with factory() as db:
                result=queue_history(db,[device_id],start=args.start,end=args.end,now=now)
                db.commit();results.append(result)
        print(json.dumps({'queued_devices':len(results),'hours_marked':sum(result['hours_marked'] for result in results),
            'raw_data_changed':False,'analysis_worker_required':True},sort_keys=True))
    finally:
        engine.dispose()


if __name__=='__main__':
    main()
