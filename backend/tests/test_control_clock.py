"""Command processing must sample wall time after waiting for the database lock."""
from datetime import timedelta
import threading

import pytest
from sqlalchemy import event, select

from app import control, worker
from app.control import create_command, advance_commands, transition
from app.db import iso, utcnow
from app.models import Command, Space, State
from app.schemas import CommandIn
from test_classrooms import sample, switch_fixture


@pytest.mark.parametrize("entrypoint", ["worker", "advance"])
def test_sqlite_lock_wait_refreshes_processing_clock(app, monkeypatch, entrypoint):
    application, _ = app
    factory = application.state.session_factory
    settings = application.state.settings
    before = utcnow()
    clock = [before]
    monkeypatch.setattr(control, "utcnow", lambda: clock[0])
    monkeypatch.setattr(worker, "utcnow", lambda: clock[0])
    with factory() as db:
        db.add(Space(id="room-A", name="A", campus_id="A", building_id="building-A",
                     kind="classroom_reference", source="test", confidence="synthetic"))
        db.flush()
        switch_fixture(db, before)
        db.commit()

    # A real BEGIN IMMEDIATE waits behind a real writer. Advance an injected wall
    # clock while it waits instead of adding a six-second sleep to every test run.
    waiting = threading.Event()
    errors = []
    engine = factory.kw["bind"]

    def beginning(_conn, _cursor, statement, _parameters, _context, _many):
        if threading.current_thread().name == "clock-regression" and statement == "BEGIN IMMEDIATE":
            waiting.set()

    def process():
        try:
            if entrypoint == "worker":
                worker.control_tick(factory, settings)
            else:
                with factory() as db:
                    advance_commands(db, settings=settings)
                    db.commit()
        except BaseException as exc:
            errors.append(exc)

    event.listen(engine, "before_cursor_execute", beginning)
    thread = threading.Thread(target=process, name="clock-regression")
    try:
        with factory() as writer:
            writer.execute(select(State).limit(1))
            thread.start()
            assert waiting.wait(5), "worker did not reach its database transaction"
            clock[0] = before + timedelta(seconds=6.2)
            sample(writer, "switch-relay-2", clock[0], 2,
                   {"desired_on": True, "actuator_reported_on": True, "fault_latched": False}, boot="b"*32)
            command, _ = create_command(writer,
                CommandIn(device_id="SIM-SWITCH", channel_id="switch-relay-2", action="shed", reason="Lock regression"),
                "clock-lock-regression", "dev-admin", clock[0], settings)
            command_id = command.id
            writer.commit()
    finally:
        thread.join(10)
        event.remove(engine, "before_cursor_execute", beginning)
    assert not thread.is_alive()
    assert not errors
    with factory() as db:
        command = db.get(Command, command_id)
        assert command.status == "dispatched", command.history
        assert command.history[-1]["at"] >= iso(command.issued_at)


def test_explicit_processing_clock_is_preserved(app, monkeypatch):
    application, _ = app
    with application.state.session_factory() as db:
        now = utcnow()
        command, _ = create_command(db,
            CommandIn(device_id="SIM-A", action="shed", reason="Explicit clock"),
            "clock-explicit-regression", "dev-admin", now, application.state.settings)
        monkeypatch.setattr(control, "utcnow", lambda: now + timedelta(days=1))
        advance_commands(db, now + timedelta(seconds=1), application.state.settings)
        assert command.status == "dispatched"
        assert command.history[-1]["at"] == iso(now + timedelta(seconds=1))


def test_production_clock_refreshes_before_each_command(app, monkeypatch):
    application, _ = app
    with application.state.session_factory() as db:
        now = utcnow()
        command, _ = create_command(db,
            CommandIn(device_id="SIM-A", action="shed", reason="Expiry after query", expires_in_seconds=2),
            "clock-expiry-regression", "dev-admin", now, application.state.settings)
        calls = iter((now, now + timedelta(seconds=3)))
        monkeypatch.setattr(control, "utcnow", lambda: next(calls))
        advance_commands(db, settings=application.state.settings)
        assert command.status == "timed_out"
        assert command.history[-1]["at"] == iso(now + timedelta(seconds=3))


def test_command_history_remains_causal_when_wall_clock_moves_backwards(app):
    application, _ = app
    with application.state.session_factory() as db:
        now = utcnow()
        command, _ = create_command(db,
            CommandIn(device_id="SIM-A", action="shed", reason="Causal history"),
            "clock-history-regression", "dev-admin", now, application.state.settings)
        transition(db, command, "dispatched", "test", now=now + timedelta(seconds=2))
        transition(db, command, "failed", "test clock adjustment", now=now - timedelta(seconds=2))
        times = [row["at"] for row in command.history]
        assert times == sorted(times)
        assert command.updated_at >= command.issued_at
        assert command.history[-1]["evidence"]["processing_clock_at"] == iso(now - timedelta(seconds=2))
