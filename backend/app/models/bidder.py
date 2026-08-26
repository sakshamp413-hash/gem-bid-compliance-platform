from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import EncryptedString


class Bidder(Base):
    __tablename__ = "bidders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(300))
    entity_type: Mapped[str] = mapped_column(String(40))  # private_limited|partnership|proprietorship|llp|pvt_ltd
    is_reseller: Mapped[bool] = mapped_column(Boolean, default=True)  # reseller bids need OEM auth
    # --- sensitive identifiers: encrypted at rest ---
    pan: Mapped[str | None] = mapped_column(EncryptedString(64))
    gstin: Mapped[str | None] = mapped_column(EncryptedString(64))
    udyam_no: Mapped[str | None] = mapped_column(EncryptedString(64))
    cin: Mapped[str | None] = mapped_column(EncryptedString(64))
    epfo_no: Mapped[str | None] = mapped_column(EncryptedString(64))
    esic_no: Mapped[str | None] = mapped_column(EncryptedString(64))
    startup_no: Mapped[str | None] = mapped_column(EncryptedString(64))
    nsic_no: Mapped[str | None] = mapped_column(EncryptedString(64))
    bank_account: Mapped[str | None] = mapped_column(EncryptedString(64))
    phone: Mapped[str | None] = mapped_column(EncryptedString(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)