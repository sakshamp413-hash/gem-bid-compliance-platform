"""RemediationTask — prioritised gap-closing action items for a bidder submission."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RemediationTask(Base):
    __tablename__ = "remediation_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("bid_submissions.id"), index=True)
    requirement_id: Mapped[str] = mapped_column(String(80))  # e.g. rule_ref or check_type
    label: Mapped[str] = mapped_column(String(300))          # human-readable gap label
    severity: Mapped[str] = mapped_column(String(20), default="medium")  # CRITICAL|HIGH|MEDIUM|LOW
    action: Mapped[str] = mapped_column(Text)                # actionable resolution step
    estimated_days: Mapped[int | None] = mapped_column(Integer, default=None)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
