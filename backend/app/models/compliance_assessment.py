from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ComplianceAssessment(Base):
    __tablename__ = "compliance_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("bid_submissions.id"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(10), default="unknown")  # low|medium|high
    pending_json: Mapped[list | None] = mapped_column(JSON, default=list)
    recommendation_text: Mapped[str | None] = mapped_column(String(3000), default=None)
    recommendation_action: Mapped[str | None] = mapped_column(String(30), default=None)  # qualify|needs_review|disqualify_candidate
    recommendation_confidence: Mapped[float | None] = mapped_column(Float, default=None)
    model_meta_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)