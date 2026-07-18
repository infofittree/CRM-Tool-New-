"""FitTree CRM — FastAPI application entry point."""

from __future__ import annotations

import logging
import os
import secrets
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

# Ensure the sales_lead_system package root is on sys.path
_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

# Pre-router import guard: in non-production environments where
# JWT_SECRET_KEY is not provided, mint an ephemeral key BEFORE importing
# the routers — api/auth.py reads SECRET_KEY at module import time, so
# this has to happen first to avoid generating two unrelated keys in the
# same process. In production we go strictly by the env (no fallback).
_is_production_at_import = bool(
    os.getenv("RAILWAY_ENVIRONMENT")
    or os.getenv("ENVIRONMENT", "").lower() == "production"
    or os.getenv("APP_ENV", "").lower() == "production"
)
_dev_ephemeral_secret_pending_warning = (
    not _is_production_at_import
    and not os.getenv("JWT_SECRET_KEY", "").strip()
)
if _dev_ephemeral_secret_pending_warning:
    os.environ["JWT_SECRET_KEY"] = secrets.token_hex(32)

from api.routers import analytics, auth, dashboard, followups, inquiries, leads, products, transfers, users

from database.db_connection import DatabaseConnection
from database.models import Base
from database.schema_manager import ensure_phase8_schema, ensure_phase9_schema, ensure_phase10_schema, ensure_phase11_schema, ensure_phase12_schema, ensure_phase13_schema, ensure_phase14_schema, ensure_phase15_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger("api").info("FitTree CRM API starting")

    # JWT_SECRET_KEY enforcement. The dev-only ephemeral secret is minted
    # at MODULE IMPORT (above the router imports) so api/auth.py sees the
    # same value. Here in lifespan we only enforce the strict production
    # contract — refuse to start if the key is missing or short.
    if _is_production_at_import:
        jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()
        if not jwt_secret or len(jwt_secret) < 32:
            raise RuntimeError(
                "JWT_SECRET_KEY must be set to a value of at least 32 characters "
                "in production. Current length: %d. Refusing to start." % len(jwt_secret)
            )
    if _dev_ephemeral_secret_pending_warning:
        logging.getLogger("api").warning(
            "JWT_SECRET_KEY not set; generated an ephemeral 256-bit key for this "
            "process (DEV ONLY — all tokens invalidate on restart)."
        )

    try:
        db = DatabaseConnection(logger=logging.getLogger("api"))
        Base.metadata.create_all(db.engine)
        logging.getLogger("api").info("Base tables created/verified")
        ensure_phase8_schema(db.engine)
        ensure_phase9_schema(db.engine)
        ensure_phase10_schema(db.engine)
        ensure_phase11_schema(db.engine)
        logging.getLogger("api").info("Phase 11 schema created")
        ensure_phase12_schema(db.engine)
        ensure_phase13_schema(db.engine)
        ensure_phase14_schema(db.engine)
        logging.getLogger("api").info("Phase 14 performance indexes applied")
        ensure_phase15_schema(db.engine)
        logging.getLogger("api").info("Phase 15 login_attempts table ensured")
    except Exception:
        logging.getLogger("api").exception("Schema migration failed")
    yield
    logging.getLogger("api").info("FitTree CRM API shutting down")


app = FastAPI(
    title="FitTree CRM API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.getLogger("api").exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

_allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers_and_options(request: Request, call_next):
    # Mint a request-id early so logs and headers can correlate. Honor an
    # incoming X-Request-ID when present so callers (mobile apps, proxies)
    # can supply their own.
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    request.state.request_id = request_id

    response = await call_next(request)
    if request.method == "OPTIONS" and response.status_code >= 400:
        return Response(status_code=200)
    # Security headers for all responses
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self';"
    )
    response.headers["X-Request-ID"] = request_id
    return response

# Suppress noisy OPTIONS request logging
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(leads.router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(followups.router, prefix="/api/v1/followups", tags=["followups"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(inquiries.router, prefix="/api/v1", tags=["inquiries"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(transfers.router, prefix="/api/v1", tags=["transfers"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])


# ── Serve Frontend Static Files ──────────────────────────────────────────
_dist_dir = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
if _dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist_dir / "assets")), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = (_dist_dir / path).resolve()
        # Security: prevent path traversal — reject anything outside web/dist
        if not str(file_path).startswith(str(_dist_dir.resolve())):
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})
        if file_path.is_file():
            return Response(
                content=file_path.read_bytes(),
                media_type="text/html" if path.endswith(".html") else None,
            )
        # SPA fallback — serve index.html for all non-API, non-asset routes
        index = _dist_dir / "index.html"
        if index.exists():
            return Response(content=index.read_bytes(), media_type="text/html")
        return JSONResponse(status_code=404, content={"detail": "Not found"})
