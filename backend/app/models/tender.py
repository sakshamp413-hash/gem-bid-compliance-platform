from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gem_ref: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    buyer_org: Mapped[str] = mapped_column(String(300))
    eligibility_json: Mapped[dict] = mapped_column(JSON, default=dict)  # raw eligibility clause
    local_content_class_required: Mapped[str | None] = mapped_column(String(10), default=None)  # I | II | None
    msme_only: Mapped[bool] = mapped_column(Boolean, default=False)
    min_turnover_crore: Mapped[float | None] = mapped_column(default=None)
    required_docs_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)