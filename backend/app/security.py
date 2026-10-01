"""Opaque revocable sessions; no JWT signing key or production default password."""
import hashlib
import hmac
import secrets
from datetime import timedelta
from fastapi import Depends, Request
from sqlalchemy import select, func
from .common import DomainError, audit
from .db import utcnow, iso
from .models import User, Session, LoginAttempt

COOKIE = "carbentra_session"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"


def verify_password(password, encoded):
    if not encoded:
        # Do equivalent expensive work for nonexistent users.
        hashlib.pbkdf2_hmac("sha256", password.encode(), b"invalid-login-salt", 600_000)
        return False
    try:
        kind, iterations, salt, expected = encoded.split("$")
        if kind != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def get_db(request: Request):
    with request.app.state.session_factory() as db:
        if db.bind.dialect.name == "sqlite":
            # SQLite has one writer. Reserve write intent before authentication reads
            # to avoid WAL read→write upgrade races; ordinary GETs remain concurrent.
            db.connection(execution_options={"sqlite_write": request.method not in SAFE_METHODS})
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


def current_user(request: Request, db=Depends(get_db)):
    raw = request.cookies.get(COOKIE)
    session = db.get(Session, token_hash(raw)) if raw else None
    if not session or session.expires_at <= utcnow():
        raise DomainError("unauthenticated", "Please sign in", 401)
    user = db.get(User, session.user_id)
    if not user or not user.enabled or user.role not in {"admin", "operator", "analyst", "viewer"} or (user.is_dev_fixture and not request.app.state.settings.dev_auth):
        raise DomainError("unauthenticated", "Session is no longer valid", 401)
    if (request.app.state.settings.deployment_mode == "public_simulation" and user.role == "viewer"
            and request.method not in SAFE_METHODS and request.url.path != "/api/v1/auth/logout"):
        raise DomainError("forbidden", "Public simulation visitors have read-only access", 403)
    if request.method not in SAFE_METHODS:
        csrf = request.headers.get("X-CSRF-Token", "")
        if not csrf or not hmac.compare_digest(csrf.encode("utf-8"), session.csrf_token.encode("utf-8")):
            raise DomainError("csrf_failed", "Missing or invalid CSRF token", 403)
    db.info["campus_ids"] = user.campus_ids
    db.info["actor"] = user.id
    request.state.auth_session = session
    return user


def roles(*allowed):
    def authorize(user=Depends(current_user)):
        if user.role not in allowed:
            raise DomainError("forbidden", "Your role is not authorized for this action", 403)
        return user
    return authorize


def global_admin(user=Depends(current_user)):
    if user.role != "admin" or user.campus_ids is not None:
        raise DomainError("global_administrator_required", "This configuration affects all campuses and requires a global administrator", 403)
    return user


def user_payload(user):
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role, "campus_ids": user.campus_ids}


def auth_payload(user, session):
    return {"user": user_payload(user), "csrf_token": session.csrf_token, "expires_at": iso(session.expires_at)}


def client_address(request):
    """Forwarded headers are ignored unless the immediate peer is explicitly trusted."""
    import ipaddress
    direct = request.client.host if request.client else "unknown"
    networks = [ipaddress.ip_network(x) for x in request.app.state.settings.trusted_proxy_cidrs]
    def trusted(value):
        try:
            return any(ipaddress.ip_address(value) in network for network in networks)
        except ValueError:
            return False
    if not trusted(direct):
        return direct
    chain = [x.strip() for x in request.headers.get("X-Forwarded-For", "").split(",") if x.strip()]
    for value in reversed(chain):
        try:
            ipaddress.ip_address(value)
        except ValueError:
            return direct
        if not trusted(value):
            return value
    return direct


def login(db, settings, body, address):
    now = utcnow()
    address_digest = token_hash(address)
    account_digest = token_hash(body.username.casefold())
    failures = db.scalar(select(func.count()).select_from(LoginAttempt).where(
        LoginAttempt.address_hash == address_digest, LoginAttempt.account_hash == account_digest,
        LoginAttempt.at > now - timedelta(minutes=5), LoginAttempt.succeeded.is_(False)))
    account_failures = db.scalar(select(func.count()).select_from(LoginAttempt).where(
        LoginAttempt.account_hash == account_digest, LoginAttempt.at > now-timedelta(minutes=15), LoginAttempt.succeeded.is_(False)))
    address_failures = db.scalar(select(func.count()).select_from(LoginAttempt).where(
        LoginAttempt.address_hash == address_digest, LoginAttempt.at > now-timedelta(minutes=1), LoginAttempt.succeeded.is_(False)))
    if failures >= 8 or account_failures >= 50 or address_failures >= 200:
        raise DomainError("rate_limited", "Too many failed sign-ins for this account or client; retry later", 429)
    user = db.scalar(select(User).where(User.username == body.username))
    valid = False
    if user and user.enabled and user.is_dev_fixture and settings.dev_auth and settings.env != "production":
        valid = hmac.compare_digest(body.password.encode("utf-8"), b"development-only")
    elif user and user.enabled and not user.is_dev_fixture:
        valid = verify_password(body.password, user.password_hash)
    else:
        verify_password(body.password, None)
    db.add(LoginAttempt(address_hash=address_digest, account_hash=account_digest, succeeded=valid))
    if not valid:
        db.commit()  # Failure rate limits survive rejected HTTP requests and restarts.
        raise DomainError("invalid_credentials", "Invalid username or password", 401)
    token = secrets.token_urlsafe(48)
    session = Session(token_hash=token_hash(token), user_id=user.id, csrf_token=secrets.token_urlsafe(32), expires_at=now + timedelta(hours=settings.session_hours))
    db.add(session)
    audit(db, user.id, "login", "session", user.id)
    db.commit()
    return token, user, session


def adapter_auth(request: Request):
    configured = request.app.state.settings.adapter_token
    if not configured:
        raise DomainError("ingestion_unconfigured", "An operator-managed adapter identity is required", 503)
    supplied = request.headers.get("Authorization", "")
    if not supplied.startswith("Bearer ") or not hmac.compare_digest(supplied[7:].encode("utf-8"), configured.get_secret_value().encode("utf-8")):
        raise DomainError("adapter_unauthorized", "Invalid adapter identity", 401)
    return "adapter"


def bootstrap_users(db, settings):
    if settings.dev_auth:
        for role in ("admin", "operator", "analyst", "viewer"):
            existing = db.scalar(select(User).where(User.username == role))
            if existing and not existing.is_dev_fixture:
                continue
            if not existing:
                db.add(User(id=f"dev-{role}", username=role, display_name=f"开发演示 · {role}", role=role, is_dev_fixture=True))
    if settings.admin_password:
        existing = db.scalar(select(User).where(User.username == settings.admin_username))
        if existing and existing.is_dev_fixture:
            raise RuntimeError("Production bootstrap username conflicts with a development fixture")
        if not existing:
            db.add(User(id="operator-admin", username=settings.admin_username, display_name="Platform administrator", role="admin", password_hash=password_hash(settings.admin_password.get_secret_value()), is_dev_fixture=False))
    db.commit()

    if settings.env == "production":
        administrators = db.scalars(select(User).where(User.role == "admin", User.enabled.is_(True), User.is_dev_fixture.is_(False))).all()
        if not any(user.campus_ids is None for user in administrators):
            raise RuntimeError("Production requires an enabled global operator-provisioned administrator; supply CARBENTRA_ADMIN_PASSWORD for first bootstrap")
