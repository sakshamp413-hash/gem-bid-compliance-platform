from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BidSubmission(Base):
    __tablename__ = "bid_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tender_id: Mapped[int] = mapped_column(ForeignKey("tenders.id"), index=True)
    bidder_id: Mapped[int] = mapped_column(ForeignKey("bidders.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="submitted")  # submitted|under_review|assessed|accepted|rejected|requested_docs
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)