import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from . import __version__
from .common import DomainError
from .config import Settings
from .db import Base, make_engine, make_session_factory
from .models import State
from . import scoping  # registers query authorization invariants
from .invariants import install_database_invariants
from .security import bootstrap_users
from .seed import seed_demo
from .worker import run_worker
from .routes import router

logger = logging.getLogger(__name__)


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # Bound storage before handing JSON bytes to the framework, including chunked bodies.
        chunks, total = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > self.max_bytes:
                response = JSONResponse({"error": {"code": "payload_too_large", "message": "Request body exceeds configured limit", "request_id": uuid4().hex}}, status_code=413)
                return await response(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        headers = dict(scope.get("headers", []))
        media_type = headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower()
        json_body = not media_type or media_type == b"application/json" or (media_type.startswith(b"application/") and media_type.endswith(b"+json"))
        if chunks and json_body and total:
            def unique_pairs(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("Duplicate JSON object keys are prohibited")
                    result[key] = value
                return result
            def reject_constant(value):
                raise ValueError("Non-finite JSON constants are prohibited")
            def finite_float(value):
                import math
                result = float(value)
                if not math.isfinite(result):
                    raise ValueError("Non-finite JSON numeric literal")
                return result
            try:
                json.loads(b"".join(chunks), object_pairs_hook=unique_pairs, parse_constant=reject_constant, parse_float=finite_float)
            except (ValueError, UnicodeDecodeError, RecursionError):
                response = JSONResponse({"error": {"code": "invalid_json", "message": "JSON must be well-formed, finite and contain unique object keys", "request_id": uuid4().hex}}, status_code=422)
                return await response(scope, receive, send)
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()
        await self.app(scope, bounded_receive, send)


def create_app(settings=None):
    settings = settings or Settings()
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    stop = threading.Event()

    @asynccontextmanager
    async def lifespan(app):
        if settings.auto_migrate:
            Base.metadata.create_all(engine)
            with engine.begin() as connection:
                install_database_invariants(connection)
        with factory() as db:
            db.execute(select(State).limit(1))
            bootstrap_users(db, settings)
            if settings.seed_demo:
                seed_demo(db, settings)
        worker = None
        if settings.worker_enabled:
            worker = threading.Thread(target=run_worker, args=(factory, settings, stop), name="campus-worker", daemon=True)
            worker.start()
        yield
        stop.set()
        if worker:
            await asyncio.to_thread(worker.join, 10)
        engine.dispose()

    app = FastAPI(title="CARBENTRA Campus API", version=__version__, lifespan=lifespan,
        docs_url=None, openapi_url="/api/openapi.json" if settings.enable_docs else None, redoc_url=None)
    app.state.settings, app.state.engine, app.state.session_factory = settings, engine, factory
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "Authorization", "Last-Event-ID"], expose_headers=["X-Request-ID"])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_body_bytes)

    @app.middleware("http")
    async def security_headers(request, call_next):
        request.state.request_id = uuid4().hex
        origin = request.headers.get("Origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in settings.allowed_origins:
            return JSONResponse({"error": {"code": "origin_denied", "message": "Request origin is not permitted", "request_id": request.state.request_id}}, status_code=403)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if settings.env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def error_response(request, code, message, status, details=None):
        error = {"code": code, "message": message, "request_id": getattr(request.state, "request_id", uuid4().hex)}
        if details is not None:
            error["details"] = details
        return JSONResponse({"error": error}, status_code=status)

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError):
        return error_response(request, exc.code, exc.message, exc.status, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc):
        # Never echo password, bearer token or raw request body into errors/logs.
        details = [{"location": list(e["loc"]), "type": e["type"], "message": e["msg"]} for e in exc.errors()]
        return error_response(request, "validation_error", "Request validation failed", 422, details)

    @app.exception_handler(ResponseValidationError)
    async def response_validation_error(request: Request, exc):
        # Validation inputs can contain an accidental internal field. Never log them.
        logger.error("Public response contract failed (%s): %s", getattr(request.state, "request_id", "unknown"),
            [{"location": list(e["loc"]), "type": e["type"]} for e in exc.errors()])
        return error_response(request, "response_contract_violation", "Response failed the public data contract", 500)

    @app.exception_handler(IntegrityError)
    async def integrity_error(request: Request, exc):
        return error_response(request, "conflict", "The operation conflicts with persisted state; refresh and retry with the same idempotency key", 409)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc):
        logger.exception("Request failed (%s)", getattr(request.state, "request_id", "unknown"))
        return error_response(request, "internal_error", "Request failed; use the request ID to locate server diagnostics", 500)

    @app.get("/health/live", tags=["health"])
    def live():
        return {"status": "alive", "version": __version__}

    @app.get("/health/ready", tags=["health"])
    def ready():
        try:
            with factory() as db:
                db.execute(select(State).limit(1))
            return {"status": "ready", "database": "connected"}
        except Exception:
            return JSONResponse({"status": "not_ready", "database": "unavailable"}, status_code=503)

    app.include_router(router)
    from .classroom_routes import router as classroom_router
    app.include_router(classroom_router)
    from fastapi.openapi.utils import get_openapi
    def domain_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes,
            description="Full-campus resource-scoped API. Seeded operational data is SIMULATED. Unknown values remain null. Physical dispatch is release-gated and disabled by default.")
        schema.setdefault("components", {}).setdefault("securitySchemes", {}).update({
            "SessionCookie": {"type": "apiKey", "in": "cookie", "name": "carbentra_session"},
            "AdapterBearer": {"type": "http", "scheme": "bearer", "description": "Operator-managed adapter identity with explicit device allowlist"}})
        for path, item in schema["paths"].items():
            for method, operation in item.items():
                if not isinstance(operation, dict) or method not in {"get", "post", "put", "patch", "delete"}:
                    continue
                adapter = path.startswith(("/api/v1/ingest/", "/api/v1/adapter/"))
                protected = path.startswith("/api/v1/") and path != "/api/v1/auth/login"
                if adapter:
                    operation["security"] = [{"AdapterBearer": []}]
                elif protected:
                    operation["security"] = [{"SessionCookie": []}]
                    if method != "get":
                        operation.setdefault("parameters", []).append({"name": "X-CSRF-Token", "in": "header", "required": True, "schema": {"type": "string"}, "description": "CSRF token from the authenticated session"})
        app.openapi_schema = schema
        return schema
    app.openapi = domain_openapi
    if settings.enable_docs:
        @app.get("/api/docs", include_in_schema=False)
        def offline_api_reference():
            from fastapi.responses import HTMLResponse
            from html import escape
            schema = app.openapi()
            rows = []
            for path, operations in schema["paths"].items():
                for method, operation in operations.items():
                    if method not in {"get", "post", "put", "patch", "delete"}:
                        continue
                    security = "adapter bearer" if any("AdapterBearer" in x for x in operation.get("security", [])) else "session + CSRF" if method != "get" and operation.get("security") else "session" if operation.get("security") else "public"
                    rows.append(f"<tr><td>{escape(method.upper())}</td><td><code>{escape(path)}</code></td><td>{escape(operation.get('summary',''))}</td><td>{security}</td></tr>")
            body = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CARBENTRA API reference</title>
            <style>body{font:16px/1.6 system-ui,sans-serif;max-width:1200px;margin:48px auto;padding:0 24px;color:#20332c;background:#f7faf7}h1{font-size:32px}a{color:#126644}table{width:100%;border-collapse:collapse;background:white}td,th{text-align:left;border-bottom:1px solid #dde6df;padding:12px}code{font-size:13px}p{max-width:850px}.note{padding:16px;background:#e9f3eb;border-radius:12px}</style>
            <h1>CARBENTRA Campus API</h1><p>Self-hosted reference. This page loads no external scripts, fonts or services.</p>
            <p><a href="/api/openapi.json">Download the complete OpenAPI JSON</a> for request schemas and client generation.</p>
            <p class="note">Operational data in the demonstration is SIMULATED. Unknown quantities remain null. Cookie-authenticated writes require X-CSRF-Token. Adapter routes require a separately provisioned bearer identity and an explicit device allowlist. Physical dispatch is disabled by default.</p>
            <table><thead><tr><th>Method</th><th>Path</th><th>Operation</th><th>Authentication</th></tr></thead><tbody>"""+"".join(rows)+"</tbody></table></html>"
            return HTMLResponse(body)
    spatial_dir = settings.spatial_seed_path.parent
    if spatial_dir.is_dir():
        app.mount("/assets/spatial", StaticFiles(directory=spatial_dir), name="spatial")
    return app


app = create_app()
