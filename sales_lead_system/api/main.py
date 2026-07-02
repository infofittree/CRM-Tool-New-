"""FitTree CRM — FastAPI application entry point."""

from __future__ import annotations

import logging
import os
import sys
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

from api.routers import analytics, auth, dashboard, followups, inquiries, leads, users
from database.db_connection import DatabaseConnection
from database.models import Base
from database.schema_manager import ensure_phase8_schema, ensure_phase9_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger("api").info("FitTree CRM API starting")
    try:
        db = DatabaseConnection(logger=logging.getLogger("api"))
        Base.metadata.create_all(db.engine)
        ensure_phase8_schema(db.engine)
        ensure_phase9_schema(db.engine)
    except Exception:
        logging.getLogger("api").exception("Schema migration failed (non-fatal)")
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
async def suppress_options_errors(request: Request, call_next):
    response = await call_next(request)
    if request.method == "OPTIONS" and response.status_code >= 400:
        from starlette.responses import Response
        return Response(status_code=200)
    return response


# Suppress noisy OPTIONS request logging
import logging
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(leads.router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(followups.router, prefix="/api/v1/followups", tags=["followups"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(inquiries.router, prefix="/api/v1", tags=["inquiries"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])


# ── Serve Frontend Static Files ──────────────────────────────────────────
_dist_dir = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
if _dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist_dir / "assets")), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = _dist_dir / path
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
