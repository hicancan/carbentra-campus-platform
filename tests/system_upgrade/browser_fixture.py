"""Narrow live simulator for the explicitly disposable classroom browser fixture.

Uses genuine application simulator/command logic. It refreshes only one SIMULATED
room, never weakens freshness, TTL, RBAC or physical-release gates. All other rooms
remain at their authentic historical seed or visibly stale current state.
"""
import argparse
import json
import signal
import threading
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import select, func
from app.config import Settings
from app.db import make_engine, make_session_factory, utcnow
from app.models import State, Space, Device, DeviceChannel, ChannelObservation

ROOM = 'space:search:space-unit-014436e6a31596a06d43'
parser = argparse.ArgumentParser()
parser.add_argument('--describe', action='store_true')
parser.add_argument('--serve', action='store_true')
parser.add_argument('--seconds', type=int, default=3600)
parser.add_argument('--stop-file', type=Path, default=Path('/tmp/classroom-browser-fixture.stop'))
args = parser.parse_args()
settings = Settings()
assert settings.env in {'test', 'development'} and settings.simulation_enabled
assert not settings.physical_dispatch_enabled and not settings.physical_release_ids
engine = make_engine(settings.database_url)
factory = make_session_factory(engine)
with factory() as db:
    seed = db.get(State, 'classroom_demo_seed')
    assert seed and seed.value.get('version') == 3
    room = db.get(Space, ROOM)
    devices = [d for d in db.scalars(select(Device).where(Device.space_id == ROOM)) if d.provenance.get('source') == 'deterministic-classroom-simulation-v1']
    assert len(devices) == 3 and all(x.source_mode == 'SIMULATED' and x.dispatch_mode == 'IN_PROCESS' for x in devices)
    description = {'room_id': ROOM, 'room_name': room.name, 'building_id': room.building_id, 'floor_id': room.floor_id,
        'anchor': seed.value['at'], 'seed': seed.value,
        'rooms': db.scalar(select(func.count()).select_from(Space)),
        'channels': db.scalar(select(func.count()).select_from(DeviceChannel)),
        'observations': db.scalar(select(func.count()).select_from(ChannelObservation)),
        'devices': [{'id': x.id, 'kind': x.kind, 'source_mode': x.source_mode} for x in devices],
        'scope': 'One explicitly SIMULATED room; no physical dispatch and no gate relaxation'}
    print(json.dumps(description), flush=True)
if args.describe:
    engine.dispose()
    raise SystemExit(0)
assert args.serve and 0 < args.seconds <= 7200
assert args.stop_file == Path('/tmp/classroom-browser-fixture.stop')
args.stop_file.unlink(missing_ok=True)
stop = threading.Event()
signal.signal(signal.SIGTERM, lambda *_: stop.set())
signal.signal(signal.SIGINT, lambda *_: stop.set())
from app.worker import control_tick
from app.simulation import emit_sample
from app.switch_simulation import emit_switch
from app.classroom_simulation import emit_presence

def refresh():
    while not stop.is_set():
        with factory() as db:
            for device in db.scalars(select(Device).where(Device.space_id == ROOM)):
                if device.provenance.get('source') != 'deterministic-classroom-simulation-v1':
                    continue
                assert device.source_mode == 'SIMULATED' and device.dispatch_mode == 'IN_PROCESS'
                {'switch': emit_switch, 'presence': emit_presence, 'smart_plug': emit_sample}[device.kind](db, device, utcnow())
            db.commit()
        stop.wait(15)

thread = threading.Thread(target=refresh, daemon=True)
thread.start()
started = datetime.now(timezone.utc)
try:
    while not stop.is_set() and not args.stop_file.exists() and (datetime.now(timezone.utc) - started).total_seconds() < args.seconds:
        control_tick(factory, settings)
        stop.wait(settings.worker_interval_seconds)
finally:
    stop.set()
    thread.join(timeout=30)
    engine.dispose()
    print(json.dumps({'stopped_at': datetime.now(timezone.utc).isoformat(), 'scope': 'one SIMULATED room'}), flush=True)
