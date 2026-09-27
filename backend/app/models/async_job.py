"""AsyncJob — tracks background worker job status (document processing queue)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class AsyncJob(Base):
    __tablename__ = "async_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=_new_uuid)
    job_type: Mapped[str] = mapped_column(String(60))       # document_process | assess_submission
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|running|done|failed
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    result_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    # context: e.g. {submission_id: 7, document_id: 12}
    context_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
