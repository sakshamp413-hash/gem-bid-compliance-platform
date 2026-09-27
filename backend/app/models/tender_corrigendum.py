"""TenderCorrigendum — stores corrigendum PDFs and their diff against original tender requirements."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TenderCorrigendum(Base):
    __tablename__ = "tender_corrigenda"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tender_id: Mapped[int] = mapped_column(ForeignKey("tenders.id"), index=True)
    corrigendum_number: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(300), default="Corrigendum")
    pdf_hash: Mapped[str | None] = mapped_column(String(64), default=None)  # SHA-256 of source PDF
    # diff_json: list of {field, original, updated, impact_severity: critical|high|medium|low}
    diff_json: Mapped[list | None] = mapped_column(JSON, default=list)
    # affected_bidder_ids: list of bidder IDs whose submissions are now impacted
    affected_bidder_ids: Mapped[list | None] = mapped_column(JSON, default=list)
    raw_text: Mapped[str | None] = mapped_column(Text, default=None)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
