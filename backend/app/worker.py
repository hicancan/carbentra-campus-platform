"""Independent control cadence and bounded synthetic telemetry transactions.
Roles can run in one process (two threads) or separate containers. PostgreSQL transaction
advisory locks serialize each role across replicas; no scheduler waits on a campus batch.
"""
import logging
import threading
import sys
from sqlalchemy import text, select, func
from .config import Settings
from .db import make_engine, make_session_factory, utcnow, iso
from .models import State, Command, Device, Event
from .control import advance_commands, TERMINAL

logger = logging.getLogger(__name__)


def active_count(db):
    return db.scalar(select(func.count()).select_from(Command).where(Command.status.not_in(TERMINAL)))


def save_state(db, key, values):
    state = db.get(State, key)
    if state:
        state.value = values
    else:
        db.add(State(key=key, value=values))


def lock(db, number):
    return db.bind.dialect.name != "postgresql" or db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": number})


def control_tick(factory, settings):
    with factory() as db:
        if not lock(db, 48392715):
            state = db.get(State, "worker")
            return state.value.get("last_tick_epoch") if state else None
        checked = advance_commands(db, settings=settings)
        now = utcnow()
        previous = db.get(State, "worker")
        if checked or not previous or now.timestamp()-previous.value.get("last_tick_epoch", 0) >= 1:
            save_state(db, "worker", {"status": "running", "role": "control", "last_tick_at": iso(now), "last_tick_epoch": now.timestamp(), "commands_checked": checked, "control_batch_size": settings.control_batch_size, "physical_dispatch_configured": settings.physical_dispatch_enabled})
        db.commit()
        return now.timestamp() if checked or not previous else (db.get(State, "worker").value.get("last_tick_epoch"))


def simulation_cycle(factory, settings):
    from .simulation import emit_sample
    if not settings.simulation_enabled:
        return
    with factory() as db:
        state = db.get(State, "simulation_worker")
        if state and utcnow().timestamp()-state.value.get("last_tick_epoch", 0) < settings.simulation_interval_seconds:
            return
        ids = list(db.scalars(select(Device.id).where(Device.source_mode == "SIMULATED", Device.dispatch_mode == "IN_PROCESS").order_by(Device.kind.desc(), Device.id)))
    count, completed = 0, True
    changed_campuses = set()
    for offset in range(0, len(ids), settings.simulation_batch_size):
        with factory() as db:
            if not lock(db, 48392716):
                return
            if active_count(db):
                completed = False
                break
            # Bound row locks and transaction time. A command arriving during a batch
            # never waits behind all 680 simulated devices.
            for device in db.scalars(select(Device).where(Device.id.in_(ids[offset:offset+settings.simulation_batch_size]))):
                if device.provenance.get("source") not in {"deterministic-campus-simulation-v1", "deterministic-classroom-simulation-v1"} or device.provenance.get("scenario") == "offline":
                    continue
                now = utcnow()
                if device.provenance.get("source") == "deterministic-classroom-simulation-v1" and device.last_seen_at and (now-device.last_seen_at).total_seconds() < settings.classroom_simulation_interval_seconds:
                    continue
                if device.kind == "switch":
                    from .switch_simulation import emit_switch
                    count += emit_switch(db, device, now)
                    changed_campuses.add(device.campus_id)
                    continue
                if device.kind == "presence":
                    from .classroom_simulation import emit_presence
                    count += emit_presence(db, device, now)
                    changed_campuses.add(device.campus_id)
                    continue
                from .models import Telemetry
                last = db.get(Telemetry, device.latest_telemetry_id) if device.latest_telemetry_id else None
                if last and (now-last.observed_at).total_seconds() < settings.simulation_interval_seconds:
                    continue
                if emit_sample(db, device, now):
                    count += 1
                    changed_campuses.add(device.campus_id)
            db.commit()
    if completed:
        with factory() as db:
            if lock(db, 48392716):
                now = utcnow()
                save_state(db, "simulation_worker", {"status": "running", "role": "simulation", "last_tick_at": iso(now), "last_tick_epoch": now.timestamp(), "samples": count, "batch_size": settings.simulation_batch_size})
                for campus_id in changed_campuses:
                    db.add(Event(type="telemetry.simulation_updated", entity_id=campus_id, campus_id=campus_id))
                db.commit()
                return now.timestamp()


def tick(factory, settings):
    """Deterministic convenience for tests and explicit one-shot checks."""
    control_tick(factory, settings)
    simulation_cycle(factory, settings)


def role_loop(factory, settings, stop, role):
    work = control_tick if role == "control" else simulation_cycle
    interval = settings.worker_interval_seconds if role == "control" else min(1, settings.simulation_interval_seconds)
    while not stop.is_set():
        try:
            tick_epoch = work(factory, settings)
            if tick_epoch is not None:
                from .worker_health import publish
                publish(role, tick_epoch)
        except Exception:
            logger.exception("%s tick or local heartbeat failed", role)
        stop.wait(interval)


def run_worker(factory, settings, stop=None, role="all"):
    stop = stop or threading.Event()
    if role == "analysis":
        from .analysis import run_analysis
        return run_analysis(factory,settings,stop)
    if role == "all" and settings.simulation_enabled:
        simulation = threading.Thread(target=role_loop, args=(factory, settings, stop, "simulation"), daemon=True, name="campus-simulation")
        simulation.start()
        role_loop(factory, settings, stop, "control")
        simulation.join(timeout=10)
    else:
        role_loop(factory, settings, stop, "control" if role == "all" else role)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--role", choices=["all", "control", "simulation", "analysis"], default="all")
    args = parser.parse_args()
    settings = Settings(worker_enabled=False)
    logging.basicConfig(level=logging.INFO)
    factory = make_session_factory(make_engine(settings.database_url))
    # A direct worker/analysis invocation must respect the same database identity
    # boundary as API startup, even if the public-demo supervisor was not used.
    from .public_demo import validate_database_mode
    with factory() as db:
        validate_database_mode(db, settings)
    if args.health:
        with factory() as db:
            key = "analysis_worker" if args.role == "analysis" else "simulation_worker" if args.role == "simulation" else "worker"
            state = db.get(State, key)
            tolerance = 180 if args.role == "analysis" else settings.simulation_interval_seconds*3 if args.role == "simulation" else 10
            healthy = state and utcnow().timestamp()-state.value.get("last_tick_epoch", 0) < tolerance
        raise SystemExit(0 if healthy else 1)
    run_worker(factory, settings, role=args.role)


if __name__ == "__main__":
    main()
