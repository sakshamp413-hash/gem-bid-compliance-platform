from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class VerificationCheck(Base):
    __tablename__ = "verification_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("bid_submissions.id"), index=True)
    check_type: Mapped[str] = mapped_column(String(40))  # udyam|gst|pan|mca|local_content|epfo|esic|startup|nsic|oem|digilocker|blacklist
    result: Mapped[str] = mapped_column(String(10))  # pass | fail | flag | na
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    rule_ref: Mapped[str | None] = mapped_column(String(80), default=None)
    portal_response_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)