"""VendorReadinessCache — caches Digital Twin pre-check results per (vendor, tender) pair."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class VendorReadinessCache(Base):
    __tablename__ = "vendor_readiness_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bidder_id: Mapped[int] = mapped_column(ForeignKey("bidders.id"), index=True)
    tender_id: Mapped[int] = mapped_column(ForeignKey("tenders.id"), index=True)
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    # gap_items: [{requirement_id, label, status: met|gap|unknown, severity: critical|high|medium|low}]
    gap_items: Mapped[list | None] = mapped_column(JSON, default=list)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
