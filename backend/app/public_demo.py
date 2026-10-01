"""Explicit, disposable public simulation. Never seed or reset an operational database.

The existing seed, API and workers remain the only implementation. This module adds
an isolated database identity, a one-shot initializer and bounded process supervision.
"""
import argparse
from datetime import datetime, timedelta
import signal
import subprocess
import sys
import threading

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from .config import Settings
from .db import Base, iso, make_engine, make_session_factory, utcnow
from .models import Campus, Device, State, User

MARKER_KEY = "public_simulation_deployment"
DATABASE_NAME = "carbentra_public_demo"
DATABASE_MARKER = "CARBENTRA_PUBLIC_SIMULATION_ONLY_V1:"
INITIALIZE_LOCK = 48392799


def require_isolated_database(connection, settings):
    """Read-only preflight, including before migrations. No URL-derived authority."""
    if settings.deployment_mode != "public_simulation" or settings.env != "production":
        raise RuntimeError("This command requires explicit public_simulation production-security mode")
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Public simulation requires PostgreSQL and PostGIS")
    row = connection.execute(text("""SELECT current_database(), current_user,
        shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = current_database()""")).one()
    if tuple(row) != (DATABASE_NAME, DATABASE_NAME, DATABASE_MARKER + settings.public_demo_id):
        raise RuntimeError("Database identity or bootstrap-only public simulation marker does not match; refusing mutation")
    if not connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis')")):
        raise RuntimeError("Public simulation database requires PostGIS")
    if connection.scalar(text("SELECT rolsuper OR rolcreatedb OR rolcreaterole FROM pg_roles WHERE rolname = current_user")):
        raise RuntimeError("Public simulation application must use a restricted database role")


def require_fresh_database(db):
    """All application tables must be empty, not merely devices or the seed marker."""
    for table in Base.metadata.sorted_tables:
        if db.execute(select(table).limit(1)).first() is not None:
            raise RuntimeError("Initialization requires an entirely empty migrated database; no in-place reseed or reset is supported")


def require_live_marker(db, settings, *, now=None, check_size=False):
    marker = db.get(State, MARKER_KEY)
    value = marker.value if marker else {}
    if value.get("id") != settings.public_demo_id or value.get("status") != "ready" or value.get("version") != 1:
        raise RuntimeError("Public simulation is not initialized for this deployment ID")
    try:
        expiry = value["expires_at"]
        if expiry is not None:
            deadline = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            if deadline.tzinfo is None or deadline <= (now or utcnow()):
                raise ValueError("expired")
        max_mb = min(int(value["max_database_mb"]), settings.public_demo_max_database_mb)
        if not 512 <= max_mb <= 16384:
            raise ValueError("invalid budget")
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("Public simulation lifetime is exhausted or invalid; retain evidence and provision a new isolated instance") from None
    if check_size:
        size = db.scalar(text("SELECT pg_database_size(current_database())"))
        if size >= max_mb * 1024 * 1024:
            raise RuntimeError("Public simulation database budget exhausted; all writers must stop")
    return value


def preflight_database_mode(connection, settings):
    """Read-only guard BEFORE schema creation/migration or account bootstrap."""
    if settings.deployment_mode == "public_simulation":
        require_isolated_database(connection, settings)
        return
    if connection.dialect.name == "postgresql":
        comment = connection.scalar(text("SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = current_database()"))
        if comment and comment.startswith(DATABASE_MARKER):
            raise RuntimeError("An isolated public simulation database cannot be repurposed as production")
    if inspect(connection).has_table(State.__tablename__):
        marker = connection.scalar(select(State.value).where(State.key == MARKER_KEY))
        if marker is not None:
            raise RuntimeError("A public simulation database cannot be opened as a standard deployment")


def validate_database_mode(db, settings):
    """Do this before any startup bootstrap writes, even when mode was changed."""
    if settings.deployment_mode == "public_simulation":
        require_isolated_database(db.connection(), settings)
        require_live_marker(db, settings, check_size=True)
    elif db.get(State, MARKER_KEY):
        raise RuntimeError("A public simulation database cannot be opened as a standard deployment")
    elif db.bind.dialect.name == "postgresql":
        comment = db.scalar(text("SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = current_database()"))
        if comment and comment.startswith(DATABASE_MARKER):
            raise RuntimeError("An isolated public simulation database cannot be repurposed as production")


def initialize(engine, settings, confirmation):
    if confirmation != settings.public_demo_id or not confirmation:
        raise RuntimeError("Explicit isolated deployment ID confirmation is required")
    secrets = (settings.admin_password, settings.public_demo_operator_password, settings.public_demo_visitor_password)
    if any(secret is None for secret in secrets):
        raise RuntimeError("Initialization requires three separately supplied account passwords")
    if len({secret.get_secret_value() for secret in secrets}) != 3:
        raise RuntimeError("Administrator, operator and visitor passwords must be different")
    with engine.connect() as connection:
        require_isolated_database(connection, settings)
        connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": INITIALIZE_LOCK})
        connection.commit()
        try:
            with Session(bind=connection, expire_on_commit=False) as db:
                existing = db.get(State, MARKER_KEY)
                if existing and existing.value.get("status") == "ready":
                    # Completed Compose jobs can restart; verify a no-op, never reseed.
                    require_live_marker(db, settings, check_size=True)
                    from .security import verify_password
                    for username, secret, role in (
                        (settings.admin_username, settings.admin_password, "admin"),
                        (settings.public_demo_operator_username, settings.public_demo_operator_password, "operator"),
                        (settings.public_demo_visitor_username, settings.public_demo_visitor_password, "viewer"),
                    ):
                        user = db.scalar(select(User).where(User.username == username))
                        if not user or user.role != role or not user.enabled or user.is_dev_fixture or not verify_password(secret.get_secret_value(), user.password_hash):
                            raise RuntimeError("Existing demo accounts do not match initialization secrets; refusing mutation")
                    return
                require_fresh_database(db)
                # Seed has intentional transaction boundaries. Persist a failure marker
                # first so an interrupted seed can never be resumed over unknown data.
                started = utcnow()
                db.add(State(key=MARKER_KEY, value={"version": 1, "id": confirmation, "status": "initializing", "started_at": iso(started)}))
                db.commit()
                from .seed import seed_demo
                seed_demo(db, settings)
                campus_ids = list(db.scalars(select(Campus.id).order_by(Campus.id)))
                if not campus_ids or db.scalar(select(Device.id).where(
                    (Device.source_mode != "SIMULATED") | (Device.dispatch_mode != "IN_PROCESS")
                ).limit(1)):
                    raise RuntimeError("Public simulation seed must contain only simulated in-process devices")
                from .security import bootstrap_users, password_hash
                bootstrap_users(db, settings)
                for ident, username, display_name, role, secret in (
                    ("public-demo-visitor", settings.public_demo_visitor_username, "Public simulation visitor", "viewer", settings.public_demo_visitor_password),
                    ("public-demo-operator", settings.public_demo_operator_username, "Private simulation operator", "operator", settings.public_demo_operator_password),
                ):
                    db.add(User(id=ident, username=username, display_name=display_name, role=role,
                                campus_ids=campus_ids, password_hash=password_hash(secret.get_secret_value()), is_dev_fixture=False))
                db.flush()
                # Local to this disposable database, not a change to the operational schema.
                db.execute(text("""ALTER TABLE devices ADD CONSTRAINT public_demo_devices_only CHECK (
                    source_mode = 'SIMULATED' AND dispatch_mode = 'IN_PROCESS' AND physical_release_id IS NULL)"""))
                db.execute(text("""ALTER TABLE users ADD CONSTRAINT public_demo_visitor_readonly CHECK (
                    NOT is_dev_fixture AND (id <> 'public-demo-visitor' OR (role = 'viewer' AND campus_ids IS NOT NULL)))"""))
                ready_at = utcnow()
                db.get(State, MARKER_KEY).value = {
                    "version": 1, "id": confirmation, "status": "ready", "started_at": iso(started),
                    "ready_at": iso(ready_at), "expires_at": iso(ready_at + timedelta(hours=settings.public_demo_lifetime_hours)) if settings.public_demo_lifetime_hours else None,
                    "max_database_mb": settings.public_demo_max_database_mb, "source_mode": "SIMULATED",
                    "physical_dispatch": False, "visitor_user_id": "public-demo-visitor", "operator_user_id": "public-demo-operator",
                }
                db.commit()
                require_live_marker(db, settings, check_size=True)
        finally:
            connection.rollback()
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": INITIALIZE_LOCK})
            connection.commit()


def allowed_request(method, path):
    """Freeze identities/topology; keep existing RBAC/CSRF for controlled demo actions."""
    if path.startswith(("/api/v1/ingest/", "/api/v1/adapter/")):
        return False
    if method in {"GET", "HEAD", "OPTIONS"}:
        return True
    if path in {"/api/v1/auth/login", "/api/v1/auth/logout"}:
        return True
    # Only already implemented simulated operational actions are available. Matching
    # by complete path components avoids allowing future administrative endpoints.
    import re
    operations = {
        "POST": (
            r"/api/v1/commands", r"/api/v1/alarms/[^/]+/(?:acknowledge|resolve|notes)",
            r"/api/v1/forecasts/refresh", r"/api/v1/strategies",
            r"/api/v1/strategies/[^/]+/(?:evaluate|approve|dispatch)", r"/api/v1/reports",
            r"/api/v1/classrooms/anomalies/evaluate",
            r"/api/v1/classrooms/anomalies/[^/]+/(?:acknowledge|resolve)",
            r"/api/v1/classrooms/policies/[^/]+/evaluate",
            r"/api/v1/classrooms/evaluations/[^/]+/dispatch", r"/api/v1/classrooms/[^/]+/policies",
        ),
        "PATCH": (r"/api/v1/classrooms/policies/[^/]+", r"/api/v1/classrooms/[^/]+/mode"),
    }
    return any(re.fullmatch(pattern, path) for pattern in operations.get(method, ()))


def supervise(settings, role):
    """Fail closed after lifetime/size exhaustion; never destroy append-only evidence."""
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    stopped = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stopped.set())
    commands = {
        "api": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers", "--limit-concurrency", "64"],
        "worker": [sys.executable, "-m", "app.worker"],
        "analysis": [sys.executable, "-m", "app.worker", "--role", "analysis"],
    }
    process = None
    try:
        while not stopped.is_set():
            with factory() as db:
                validate_database_mode(db, settings)
            if process is None:
                process = subprocess.Popen(commands[role])
            if process.poll() is not None:
                return process.returncode
            stopped.wait(15)
        return 0
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("migrate", "initialize", "api", "worker", "analysis", "check"))
    parser.add_argument("--confirm-isolated-demo")
    args = parser.parse_args()
    settings = Settings()
    if settings.deployment_mode != "public_simulation":
        raise SystemExit("This entrypoint is only for isolated public simulation")
    if args.action in {"api", "worker", "analysis"}:
        raise SystemExit(supervise(settings, args.action))
    engine = make_engine(settings.database_url)
    try:
        if args.action == "initialize":
            initialize(engine, settings, args.confirm_isolated_demo)
        else:
            with engine.connect() as connection:
                require_isolated_database(connection, settings)
            if args.action == "migrate":
                from .migrate import main as migrate
                migrate()
            else:
                with make_session_factory(engine)() as db:
                    require_live_marker(db, settings, check_size=True)
        print(f"Public simulation {args.action}: passed")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
