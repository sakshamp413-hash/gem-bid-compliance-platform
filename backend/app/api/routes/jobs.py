"""
Async Job status endpoints (F07).

GET /jobs/{job_id}  → {job_id, status, progress_pct, result_json}
POST /jobs/document — enqueue a document processing job
POST /jobs/assess   — enqueue a submission assessment job
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(
    job_id: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Poll async job status. Returns {job_id, status, progress_pct, result_json}."""
    from app.services.worker import get_job_status

    result = get_job_status(db, job_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Job {job_id} not found")
    return result


@router.post("/document")
def enqueue_document_job(
    document_id: int,
    submission_id: int,
    user: User = Depends(require_roles("officer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Enqueue a document processing job (OCR + PKI + tamper detection).
    Returns {job_id, status} immediately. Poll GET /jobs/{job_id} for completion.
    Falls back to synchronous processing if Redis is unavailable.
    """
    from app.services.worker import JOB_DOCUMENT_PROCESS, enqueue_job

    return enqueue_job(
        db,
        job_type=JOB_DOCUMENT_PROCESS,
        context={"document_id": document_id, "submission_id": submission_id,
                 "actor": f"user:{user.id}"},
    )


@router.post("/assess")
def enqueue_assess_job(
    submission_id: int,
    user: User = Depends(require_roles("officer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Enqueue a compliance assessment job for a submission.
    Returns {job_id, status} immediately. Poll GET /jobs/{job_id} for completion.
    Falls back to synchronous processing if Redis is unavailable.
    """
    from app.services.worker import JOB_ASSESS_SUBMISSION, enqueue_job

    return enqueue_job(
        db,
        job_type=JOB_ASSESS_SUBMISSION,
        context={"submission_id": submission_id, "actor": f"user:{user.id}"},
    )
