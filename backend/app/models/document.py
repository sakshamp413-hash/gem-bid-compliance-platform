from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("bid_submissions.id"), index=True)
    doc_type: Mapped[str] = mapped_column(String(40))  # udyam|gst_cert|pan_card|cin|oem_auth|local_content|epfo|esic|startup|nsic|blacklist_affidavit
    file_path: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str] = mapped_column(String(300), default="")
    extracted_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    ocr_confidence: Mapped[float | None] = mapped_column(default=None)
    ocr_source: Mapped[str] = mapped_column(String(30), default="")  # pdf_text|paddleocr|tesseract|none
    signature_status: Mapped[str] = mapped_column(String(20), default="not_signed")  # not_signed|valid|invalid|untrusted
    signature_detail: Mapped[dict | None] = mapped_column(JSON, default=None)
    tamper_flags_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)