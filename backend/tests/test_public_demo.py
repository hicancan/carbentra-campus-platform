"""Public simulation security policy. Optional PG test uses a fresh dedicated test DB."""
from datetime import timedelta
import os

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.config import Settings
from app.db import Base, iso, make_engine, make_session_factory, utcnow
from app.models import State, User
from app.public_demo import (MARKER_KEY, allowed_request, initialize, require_fresh_database,
                             require_live_marker, validate_database_mode)


def production_settings(**changes):
    values = dict(env="production", database_url="postgresql+psycopg://app@db/production",
                  cookie_secure=True, auto_migrate=False, worker_enabled=False,
                  allowed_origins=["https://demo.example.org"], trusted_hosts=["demo.example.org", "localhost", "127.0.0.1"])
    return Settings(**(values | changes))


def demo_settings(**changes):
    return production_settings(**(dict(deployment_mode="public_simulation", public_demo_id="test-generation",
        database_url="postgresql+psycopg://carbentra_public_demo@db/carbentra_public_demo", simulation_enabled=True) | changes))


@pytest.mark.parametrize("changes", [
    {"env": "development"}, {"dev_auth": True}, {"seed_demo": True}, {"auto_migrate": True},
    {"cookie_secure": False}, {"simulation_enabled": False}, {"worker_enabled": True},
    {"public_demo_id": None}, {"public_demo_id": "invalid ID"},
    {"physical_dispatch_enabled": True}, {"physical_release_ids": ["release-anything"]},
    {"adapter_token": "a" * 40}, {"adapter_allowed_device_ids": ["DEVICE"]},
    {"database_url": "postgresql+psycopg://carbentra@db/carbentra"},
    {"database_url": "postgresql+psycopg://carbentra_public_demo@db/production"},
    {"public_demo_operator_username": "visitor"}, {"public_demo_visitor_username": "admin"},
    {"public_demo_visitor_password": "short"}, {"public_demo_operator_password": "short"},
])
def test_demo_configuration_fails_closed(changes):
    with pytest.raises(ValidationError):
        demo_settings(**changes)


def test_standard_production_cannot_silently_enable_simulation():
    assert production_settings().deployment_mode == "standard"
    with pytest.raises(ValidationError, match="isolated"):
        production_settings(simulation_enabled=True)
    assert demo_settings().simulation_enabled
    assert demo_settings().public_demo_lifetime_hours == 0


@pytest.mark.parametrize("method,path,allowed", [
    ("GET", "/api/v1/devices", True), ("POST", "/api/v1/auth/login", True),
    ("POST", "/api/v1/auth/logout", True), ("POST", "/api/v1/commands", True),
    ("POST", "/api/v1/classrooms/evaluations/example/dispatch", True),
    ("PATCH", "/api/v1/classrooms/example/mode", True),
    ("POST", "/api/v1/users", False), ("PATCH", "/api/v1/users/public-demo-visitor", False),
    ("POST", "/api/v1/devices", False), ("PUT", "/api/v1/devices/example/binding", False),
    ("POST", "/api/v1/devices/example/commissioning/release", False),
    ("POST", "/api/v1/ingest/events", False), ("GET", "/api/v1/adapter/commands", False),
    ("POST", "/api/v1/commands/new-admin-feature", False),
])
def test_demo_request_allowlist(method, path, allowed):
    assert allowed_request(method, path) is allowed


@pytest.fixture
def unit_db(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'public-demo-unit.db'}")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as db:
        yield db
    engine.dispose()


def marker(settings, expires_at=None):
    return State(key=MARKER_KEY, value={"version": 1, "id": settings.public_demo_id, "status": "ready",
        "expires_at": iso(expires_at or utcnow() + timedelta(hours=1)), "max_database_mb": 1024})


def test_initialization_rejects_any_preexisting_domain_data(unit_db):
    require_fresh_database(unit_db)
    unit_db.add(State(key="operational-setting", value={"private": True}))
    unit_db.commit()
    with pytest.raises(RuntimeError, match="empty"):
        require_fresh_database(unit_db)
    assert unit_db.get(State, "operational-setting").value == {"private": True}


def test_marker_identity_and_expiry_are_fail_closed(unit_db):
    settings = demo_settings()
    with pytest.raises(RuntimeError, match="not initialized"):
        require_live_marker(unit_db, settings)
    unit_db.add(marker(settings))
    unit_db.commit()
    assert require_live_marker(unit_db, settings)["id"] == settings.public_demo_id
    with pytest.raises(RuntimeError, match="not initialized"):
        require_live_marker(unit_db, demo_settings(public_demo_id="other-generation"))
    with pytest.raises(RuntimeError, match="lifetime"):
        require_live_marker(unit_db, settings, now=utcnow() + timedelta(days=1))
    with pytest.raises(RuntimeError, match="standard deployment"):
        validate_database_mode(unit_db, production_settings())


def test_initialize_requires_explicit_confirmation_and_separate_secrets():
    with pytest.raises(RuntimeError, match="confirmation"):
        initialize(None, demo_settings(), None)
    with pytest.raises(RuntimeError, match="passwords"):
        initialize(None, demo_settings(), "test-generation")
    with pytest.raises(RuntimeError, match="different"):
        initialize(None, demo_settings(admin_password="same-only-for-testing-secret", public_demo_operator_password="same-only-for-testing-secret",
            public_demo_visitor_password="same-only-for-testing-secret"), "test-generation")


def test_pg_fresh_init_real_auth_roles_and_guards(monkeypatch):
    url = os.environ.get("CARBENTRA_PUBLIC_DEMO_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires explicitly prepared, empty carbentra_public_demo test database")
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.models import Campus, Building, Device, Session as AuthSession
    from app.public_demo import require_isolated_database
    settings = demo_settings(database_url=url,
        admin_password="unit-administrator-distinct-secret",
        public_demo_visitor_password="unit-visitor-distinct-secret",
        public_demo_operator_password="unit-operator-distinct-secret")
    engine = make_engine(url)
    factory = make_session_factory(engine)
    # This test deliberately never drops or resets a database.
    with factory() as db:
        require_isolated_database(db.connection(), settings)
        require_fresh_database(db)
    def tiny_seed(db, settings):
        db.add(Campus(id="demo-campus", name="Synthetic fixture", source="unit-test"))
        db.flush()
        db.add(Building(id="demo-building", campus_id="demo-campus", name="Synthetic fixture", source="unit-test"))
        db.flush()
        db.add(Device(id="SIM-TEST", name="Simulation fixture", campus_id="demo-campus", building_id="demo-building", source_mode="SIMULATED", kind="smart_plug"))
        db.commit()
    monkeypatch.setattr("app.seed.seed_demo", tiny_seed)
    initialize(engine, settings, "test-generation")
    with factory() as db:
        before = db.get(State, MARKER_KEY).value.copy()
        assert len(list(db.scalars(select(User)))) == 3
        assert not any(user.is_dev_fixture for user in db.scalars(select(User)))
    initialize(engine, settings, "test-generation")
    with pytest.raises(RuntimeError, match="do not match"):
        initialize(engine, demo_settings(database_url=url, admin_password="wrong-distinct-administrator-secret",
            public_demo_visitor_password="unit-visitor-distinct-secret", public_demo_operator_password="unit-operator-distinct-secret"), "test-generation")
    with factory() as db:
        assert db.get(State, MARKER_KEY).value == before
        with pytest.raises(RuntimeError, match="standard deployment"):
            validate_database_mode(db, production_settings(database_url=url))
    from sqlalchemy.exc import IntegrityError
    with factory() as db:
        with pytest.raises(IntegrityError):
            visitor = db.get(User, "public-demo-visitor")
            visitor.role = "admin"
            db.commit()
        db.rollback()
        with pytest.raises(IntegrityError):
            device = db.get(Device, "SIM-TEST")
            device.source_mode = "REAL"
            db.commit()
        db.rollback()
    app = create_app(settings)
    with TestClient(app, base_url="https://demo.example.org") as client:
        assert client.get("/api/v1/campuses").status_code == 401
        assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "development-only"}).status_code == 401
        login = client.post("/api/v1/auth/login", json={"username": "visitor", "password": "unit-visitor-distinct-secret"})
        assert login.status_code == 200, login.text
        assert "Secure" in login.headers["set-cookie"] and "HttpOnly" in login.headers["set-cookie"]
        assert login.json()["data"]["user"]["role"] == "viewer"
        csrf = {"X-CSRF-Token": login.json()["data"]["csrf_token"]}
        assert client.get("/api/v1/campuses").status_code == 200
        assert client.post("/api/v1/commands", json={}, headers=csrf).status_code == 403
        assert client.post("/api/v1/users", json={}, headers=csrf).status_code == 403
        assert client.post("/api/v1/ingest/events", json={}).status_code == 403
        assert client.post("/api/v1/auth/logout", headers=csrf).status_code == 200
        login = client.post("/api/v1/auth/login", json={"username": "simulation-operator", "password": "unit-operator-distinct-secret"})
        assert login.status_code == 200
        assert login.json()["data"]["user"]["role"] == "operator"
        assert client.post("/api/v1/commands", json={}).status_code == 403
        csrf = {"X-CSRF-Token": login.json()["data"]["csrf_token"]}
        # Reaching body validation proves operator authorization; it is not an actuation claim.
        assert client.post("/api/v1/commands", json={}, headers=csrf).status_code == 422
        assert client.post("/api/v1/devices", json={}, headers=csrf).status_code == 403
        assert client.get("/api/v1/users").status_code == 403
        with factory() as db:
            state = db.get(State, MARKER_KEY)
            state.value = state.value | {"expires_at": iso(utcnow() - timedelta(seconds=1))}
            db.commit()
        assert client.get("/api/v1/campuses").status_code == 503
    engine.dispose()


def test_persistent_demo_has_no_implicit_expiry(unit_db):
    settings = demo_settings()
    row = marker(settings)
    row.value = row.value | {"expires_at": None}
    unit_db.add(row)
    unit_db.commit()
    assert require_live_marker(unit_db, settings, now=utcnow()+timedelta(days=365))["expires_at"] is None


def test_standard_startup_rejects_marker_before_any_schema_writes(tmp_path):
    from sqlalchemy import inspect
    from fastapi.testclient import TestClient
    from app.main import create_app
    path = tmp_path / "marked-but-incomplete.db"
    engine = make_engine(f"sqlite:///{path}")
    State.__table__.create(engine)
    with make_session_factory(engine)() as db:
        db.add(State(key=MARKER_KEY, value={"id": "test-generation", "status": "initializing"}))
        db.commit()
    before = inspect(engine).get_table_names()
    assert before == [State.__tablename__]
    app = create_app(Settings(env="test", database_url=f"sqlite:///{path}", worker_enabled=False, auto_migrate=True))
    with pytest.raises(RuntimeError, match="standard deployment"):
        with TestClient(app):
            pass
    assert inspect(engine).get_table_names() == before
    with make_session_factory(engine)() as db:
        assert db.get(State, MARKER_KEY).value["status"] == "initializing"
    app.state.engine.dispose()
    engine.dispose()


def test_direct_standard_worker_refuses_marked_database_before_running(tmp_path, monkeypatch):
    from app import worker
    path = tmp_path / "marked-worker.db"
    engine = make_engine(f"sqlite:///{path}")
    State.__table__.create(engine)
    with make_session_factory(engine)() as db:
        db.add(State(key=MARKER_KEY, value={"id": "test-generation", "status": "ready"}))
        db.commit()
    settings = Settings(env="test", database_url=f"sqlite:///{path}", worker_enabled=False, simulation_enabled=True)
    monkeypatch.setattr(worker, "Settings", lambda **_: settings)
    monkeypatch.setattr(worker.sys, "argv", ["worker"])
    monkeypatch.setattr(worker, "run_worker", lambda *_a, **_k: pytest.fail("Worker ran before mode guard"))
    with pytest.raises(RuntimeError, match="standard deployment"):
        worker.main()
    engine.dispose()


def test_supervisor_terminates_child_on_budget_failure(monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from app import public_demo
    events = []
    class Child:
        def poll(self):
            return None
        def terminate(self):
            events.append("terminated")
        def wait(self, timeout=None):
            events.append("waited")
    class Stop:
        def is_set(self):
            return False
        def wait(self, seconds):
            assert seconds == 15
        def set(self):
            pass
    checks = []
    def guard(db, settings):
        checks.append(True)
        if len(checks) > 1:
            raise RuntimeError("database budget exhausted")
    monkeypatch.setattr(public_demo, "make_engine", lambda _: SimpleNamespace(dispose=lambda: events.append("disposed")))
    monkeypatch.setattr(public_demo, "make_session_factory", lambda _: lambda: nullcontext(object()))
    monkeypatch.setattr(public_demo, "validate_database_mode", guard)
    monkeypatch.setattr(public_demo.signal, "signal", lambda *_: None)
    monkeypatch.setattr(public_demo.threading, "Event", Stop)
    monkeypatch.setattr(public_demo.subprocess, "Popen", lambda _: Child())
    with pytest.raises(RuntimeError, match="budget"):
        public_demo.supervise(demo_settings(), "worker")
    assert events == ["terminated", "waited", "disposed"]
