"""
Async Worker Queue (F07) — decouples synchronous OCR/PDF pipeline from FastAPI threads.

Architecture:
  - FastAPI endpoint: enqueue job → return {job_id, status: "queued"}
  - arq worker: process job → update AsyncJob row → done/failed
  - Polling: GET /jobs/{job_id} → {status, progress_pct, result_json}

Falls back to SYNCHRONOUS processing when REDIS_URL is not set
(development / demo mode), so tests always pass without Redis.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Job type constants ─────────────────────────────────────────────────────
JOB_DOCUMENT_PROCESS = "document_process"
JOB_ASSESS_SUBMISSION = "assess_submission"


# ── Synchronous fallback ───────────────────────────────────────────────────

def _run_sync_document_process(db, context: dict) -> dict[str, Any]:
    """Inline synchronous document processing (used when Redis is unavailable)."""
    from app.models.document import Document
    from app.services.document_service import process_document_sync

    doc_id = context.get("document_id")
    if doc_id is None:
        return {"error": "no document_id in context"}
    doc = db.get(Document, doc_id)
    if doc is None:
        return {"error": f"document {doc_id} not found"}
    try:
        result = process_document_sync(db, doc)
        return {"document_id": doc_id, "result": "processed", "detail": result}
    except Exception as exc:
        return {"error": str(exc)}


def _run_sync_assess(db, context: dict) -> dict[str, Any]:
    """Inline synchronous submission assessment (used when Redis is unavailable)."""
    from app.models.bid_submission import BidSubmission
    from app.services.pipeline import run_verification

    sub_id = context.get("submission_id")
    if sub_id is None:
        return {"error": "no submission_id in context"}
    sub = db.get(BidSubmission, sub_id)
    if sub is None:
        return {"error": f"submission {sub_id} not found"}
    try:
        assessment = run_verification(db, sub, actor="async_worker")
        return {"submission_id": sub_id, "score": assessment.score, "risk": assessment.risk_level}
    except Exception as exc:
        return {"error": str(exc)}


# ── Job management ─────────────────────────────────────────────────────────

def enqueue_job(
    db,
    job_type: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    Create an AsyncJob record and attempt to enqueue via arq.
    Falls back to synchronous processing if REDIS_URL is not set.

    Returns: {job_id, status, message}
    """
    from app.core.config import settings
    from app.models.async_job import AsyncJob

    job_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Create DB record
    job = AsyncJob(
        job_id=job_id,
        job_type=job_type,
        status="queued",
        progress_pct=0.0,
        context_json=context,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Try async Redis queue, fall back to sync
    redis_url = getattr(settings, "redis_url", None)
    if redis_url:
        try:
            import asyncio
            from arq import create_pool
            from arq.connections import RedisSettings

            async def _enqueue():
                pool = await create_pool(RedisSettings.from_dsn(redis_url))
                await pool.enqueue_job(
                    f"worker_{job_type}",
                    job_id=job_id,
                    context=context,
                )
                await pool.aclose()

            asyncio.get_event_loop().run_until_complete(_enqueue())
            logger.info("job %s enqueued to Redis (type=%s)", job_id, job_type)
            return {"job_id": job_id, "status": "queued", "async": True}
        except Exception as exc:
            logger.warning("Redis enqueue failed (%s) — falling back to sync", exc)

    # Sync fallback
    job.status = "running"
    job.progress_pct = 10.0
    db.commit()
    try:
        if job_type == JOB_DOCUMENT_PROCESS:
            result = _run_sync_document_process(db, context)
        elif job_type == JOB_ASSESS_SUBMISSION:
            result = _run_sync_assess(db, context)
        else:
            result = {"error": f"unknown job_type: {job_type}"}

        job.status = "done" if "error" not in result else "failed"
        job.progress_pct = 100.0
        job.result_json = result
        job.error_message = result.get("error") if "error" in result else None
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        result = {"error": str(exc)}

    job.updated_at = datetime.utcnow()
    db.commit()
    logger.info("job %s completed sync (type=%s, status=%s)", job_id, job_type, job.status)
    return {"job_id": job_id, "status": job.status, "async": False, "result": result}


def get_job_status(db, job_id: str) -> dict[str, Any] | None:
    """Retrieve job status record. Returns None if not found."""
    from app.models.async_job import AsyncJob

    job = db.query(AsyncJob).filter(AsyncJob.job_id == job_id).first()
    if job is None:
        return None
    return {
        "job_id": job.job_id,
        "job_type": job.job_type,
        "status": job.status,
        "progress_pct": job.progress_pct,
        "result_json": job.result_json,
        "error_message": job.error_message,
        "context": job.context_json,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


# ── arq worker functions (loaded by arq worker process) ───────────────────

async def worker_document_process(ctx, job_id: str, context: dict):
    """arq worker task: process a document asynchronously."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.models.async_job import AsyncJob

    with Session(engine) as db:
        job = db.query(AsyncJob).filter(AsyncJob.job_id == job_id).first()
        if job:
            job.status = "running"
            job.progress_pct = 10.0
            db.commit()
        try:
            result = _run_sync_document_process(db, context)
            if job:
                job.status = "done" if "error" not in result else "failed"
                job.progress_pct = 100.0
                job.result_json = result
                job.error_message = result.get("error")
                db.commit()
        except Exception as exc:
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                db.commit()
            raise


async def worker_assess_submission(ctx, job_id: str, context: dict):
    """arq worker task: run compliance assessment asynchronously."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.models.async_job import AsyncJob

    with Session(engine) as db:
        job = db.query(AsyncJob).filter(AsyncJob.job_id == job_id).first()
        if job:
            job.status = "running"
            job.progress_pct = 10.0
            db.commit()
        try:
            result = _run_sync_assess(db, context)
            if job:
                job.status = "done" if "error" not in result else "failed"
                job.progress_pct = 100.0
                job.result_json = result
                job.error_message = result.get("error")
                db.commit()
        except Exception as exc:
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                db.commit()
            raise


class WorkerSettings:
    """arq WorkerSettings — run via: python -m arq app.services.worker.WorkerSettings"""
    functions = [worker_document_process, worker_assess_submission]
    max_jobs = 4
    job_timeout = 300  # 5 minutes
