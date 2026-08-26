"""
Document ingestion service: upload → text extraction → AI field extraction
→ signature verification → tamper analysis → persistence.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.ai.extraction import extract_document
from app.core.config import settings
from app.core.logging import get_logger
from app.db.audit import append_audit
from app.models.document import Document
from app.security.signature_verify import verify_pdf_signature
from app.security.tamper_detect import analyze_pdf_tamper

logger = get_logger(__name__)


def process_uploaded_document(
    db: Session,
    submission_id: int,
    doc_type: str,
    file_name: str,
    content: bytes,
    actor: str = "system",
) -> Document:
    """Save, extract, analyze and persist an uploaded document."""
    storage = settings.storage_dir
    safe_name = Path(file_name).name or "document.pdf"
    stored_name = f"{uuid.uuid4().hex[:12]}_{safe_name}"
    path = storage / stored_name
    path.write_bytes(content)

    doc = Document(
        submission_id=submission_id,
        doc_type=doc_type,
        file_path=str(path),
        file_name=safe_name,
    )
    db.add(doc)
    db.flush()

    # 1) extraction (OCR if needed)
    extraction: dict[str, Any] = {}
    try:
        extraction = extract_document(str(path), doc_type)
        doc.extracted_json = extraction
        doc.ocr_confidence = extraction.get("confidence")
        doc.ocr_source = extraction.get("source", "")
    except Exception as exc:
        logger.warning("extraction failed for %s: %s", file_name, exc)
        doc.extracted_json = {"doc_type": doc_type, "fields": {}, "error": str(exc)}
        doc.ocr_source = "none"

    # 2) signature verification
    sig = verify_pdf_signature(str(path))
    # A document is only "valid" when the signature is intact AND trusted;
    # any post-signing modification (intact=False) renders it invalid.
    if sig.get("signed") and sig.get("intact"):
        doc.signature_status = "valid" if sig.get("trusted") else "untrusted"
    elif sig.get("signed"):
        doc.signature_status = "invalid"
    else:
        doc.signature_status = "not_signed"
    doc.signature_detail = sig

    # 3) tamper analysis
    tamper = analyze_pdf_tamper(str(path), sig)
    doc.tamper_flags_json = tamper

    db.commit()
    db.refresh(doc)
    append_audit(
        db,
        actor=actor,
        action="upload_document",
        entity=f"document:{doc.id}",
        payload={"doc_type": doc_type, "signature_status": doc.signature_status,
                 "tampered": tamper.get("tampered")},
    )
    return doc