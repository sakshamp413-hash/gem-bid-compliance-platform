"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import engine, init_db
from app.integration.adapter import get_adapter  # noqa: F401 (register adapters on import)
from app.integration import mock, stubs  # noqa: F401 (register adapters)

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("startup: db=%s adapter=%s llm=%s",
                "postgres" if "postgres" in settings.database_url else "sqlite",
                settings.portal_adapter, settings.llm_resolved_provider)
    yield


app = FastAPI(
    title="PRAMAAN — AI-Powered GeM Bid Compliance & Procurement Intelligence Platform",
    description=(
        "PRAMAAN turns complex GeM tender requirements and bidder documents into explainable, "
        "evidence-backed compliance decisions before a bid is rejected or a procurement decision is finalized. "
        "Human-in-the-loop decision support: the system recommends, the officer decides. "
        "Interactive docs at /docs (OpenAPI)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- routes ---
from app.api.routes import (  # noqa: E402
    admin,
    audit,
    auth,
    decisions,
    documents,
    findings,
    submissions,
    tenders,
    users,
)

for r in (auth.router, users.router, tenders.router, submissions.router,
          documents.router, decisions.router, audit.router, findings.router,
          admin.router):
    app.include_router(r)


@app.get("/health", tags=["system"])
def health():
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = "ok"
    except Exception as exc:
        logger.error("health check db failed: %s", exc)
        db_ok = "error"
    return {
        "status": "ok",
        "app": settings.app_name,
        "database": db_ok,
        "adapter": settings.portal_adapter,
        "llm_provider": settings.llm_resolved_provider,
    }


@app.get("/", tags=["system"])
def root():
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }