"""
Corrigendum Impact Analyzer (F02)

Diffs original tender requirements against a corrigendum text,
identifies changed/added/removed clauses, and flags affected bidders.
"""
from __future__ import annotations

import difflib
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)

_CHANGE_SEVERITY_MAP: dict[str, str] = {
    "turnover": "critical",
    "local_content": "critical",
    "security_deposit": "critical",
    "blacklist": "critical",
    "msme": "high",
    "experience": "high",
    "oem_auth": "high",
    "gst": "high",
    "pan": "high",
    "epfo": "medium",
    "esic": "medium",
    "startup": "medium",
    "nsic": "medium",
}

_FIELD_PATTERNS: dict[str, str] = {
    "turnover": r"turnover",
    "msme": r"msme|udyam",
    "local_content": r"local\s+content|make\s+in\s+india",
    "security_deposit": r"emd|earnest\s+money|bid\s+security",
    "experience": r"experience",
    "gst": r"gstin|gst",
    "pan": r"\bpan\b",
    "oem_auth": r"oem|manufacturer\s+author",
    "epfo": r"epfo|provident\s+fund",
    "esic": r"esic",
    "deadline": r"deadline|last\s+date|submission\s+date|closing\s+date",
}


def _classify_change(text: str) -> str:
    low = text.lower()
    for field, pattern in _FIELD_PATTERNS.items():
        if re.search(pattern, low):
            return field
    return "general"


def _normalize(text: str) -> list[str]:
    """Normalize text to list of non-empty stripped lines for diffing."""
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _compute_diff(original: str, corrigendum: str) -> list[dict[str, Any]]:
    """
    Produce a list of changes between original and corrigendum texts.
    Each entry: {field, original, updated, impact_severity, change_type}
    """
    orig_lines = _normalize(original)
    corr_lines = _normalize(corrigendum)

    matcher = difflib.SequenceMatcher(None, orig_lines, corr_lines)
    changes: list[dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        orig_chunk = "\n".join(orig_lines[i1:i2]) if i1 < i2 else ""
        corr_chunk = "\n".join(corr_lines[j1:j2]) if j1 < j2 else ""

        if tag == "replace":
            change_type = "modified"
            text_for_classify = orig_chunk or corr_chunk
        elif tag == "insert":
            change_type = "added"
            text_for_classify = corr_chunk
        else:  # delete
            change_type = "removed"
            text_for_classify = orig_chunk

        field = _classify_change(text_for_classify)
        severity = _CHANGE_SEVERITY_MAP.get(field, "medium")

        changes.append({
            "field": field,
            "original": orig_chunk[:500] if orig_chunk else None,
            "updated": corr_chunk[:500] if corr_chunk else None,
            "impact_severity": severity,
            "change_type": change_type,
        })

    return changes


def _find_affected_bidders(db: Session, tender_id: int, diff: list[dict]) -> list[int]:
    """
    Identify bidder IDs whose submissions may be impacted by the corrigendum changes.
    Heuristic: any submission in 'submitted' or 'under_review' state is affected.
    For CRITICAL changes, also flag 'assessed' submissions.
    """
    from app.models.bid_submission import BidSubmission

    has_critical = any(d["impact_severity"] == "critical" for d in diff)
    statuses = ["submitted", "under_review"]
    if has_critical:
        statuses.append("assessed")

    subs = (
        db.query(BidSubmission)
        .filter(
            BidSubmission.tender_id == tender_id,
            BidSubmission.status.in_(statuses),
        )
        .all()
    )
    return list({s.bidder_id for s in subs})


def analyze_corrigendum(
    db: Session,
    tender_id: int,
    corrigendum_text: str,
    corrigendum_number: int = 1,
    title: str = "Corrigendum",
    pdf_hash: str | None = None,
) -> dict[str, Any]:
    """
    Persist a TenderCorrigendum record with diff vs. original tender requirements.
    Returns the full corrigendum analysis dict.
    """
    from app.models.tender import Tender
    from app.models.tender_corrigendum import TenderCorrigendum

    tender = db.get(Tender, tender_id)
    if tender is None:
        raise ValueError(f"Tender {tender_id} not found")

    # Build original text from tender eligibility + required docs
    original_parts = [tender.title or ""]
    elig = tender.eligibility_json or {}
    for key, val in elig.items():
        original_parts.append(f"{key}: {val}")
    if tender.min_turnover_crore:
        original_parts.append(f"Minimum Annual Turnover: {tender.min_turnover_crore} Crore")
    if tender.msme_only:
        original_parts.append("MSME Only: Yes")
    if tender.local_content_class_required:
        original_parts.append(f"Local Content Class Required: {tender.local_content_class_required}")
    original_text = "\n".join(str(p) for p in original_parts)

    diff = _compute_diff(original_text, corrigendum_text)
    affected_bidder_ids = _find_affected_bidders(db, tender_id, diff)

    corrigendum = TenderCorrigendum(
        tender_id=tender_id,
        corrigendum_number=corrigendum_number,
        title=title,
        pdf_hash=pdf_hash,
        diff_json=diff,
        affected_bidder_ids=affected_bidder_ids,
        raw_text=corrigendum_text[:10000],
        published_at=datetime.utcnow(),
    )
    db.add(corrigendum)
    db.commit()
    db.refresh(corrigendum)

    logger.info(
        "corrigendum analyzed: tender=%s, changes=%d, affected_bidders=%d",
        tender_id, len(diff), len(affected_bidder_ids),
    )

    return {
        "id": corrigendum.id,
        "tender_id": tender_id,
        "corrigendum_number": corrigendum.corrigendum_number,
        "title": corrigendum.title,
        "pdf_hash": corrigendum.pdf_hash,
        "diff": diff,
        "affected_bidder_ids": affected_bidder_ids,
        "total_changes": len(diff),
        "critical_changes": sum(1 for d in diff if d["impact_severity"] == "critical"),
        "published_at": corrigendum.published_at.isoformat(),
    }


def get_corrigenda_for_tender(db: Session, tender_id: int) -> list[dict[str, Any]]:
    """Return all corrigenda for a tender, sorted newest first."""
    from app.models.tender_corrigendum import TenderCorrigendum

    rows = (
        db.query(TenderCorrigendum)
        .filter(TenderCorrigendum.tender_id == tender_id)
        .order_by(TenderCorrigendum.corrigendum_number.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "tender_id": r.tender_id,
            "corrigendum_number": r.corrigendum_number,
            "title": r.title,
            "pdf_hash": r.pdf_hash,
            "diff": r.diff_json,
            "affected_bidder_ids": r.affected_bidder_ids,
            "total_changes": len(r.diff_json or []),
            "critical_changes": sum(
                1 for d in (r.diff_json or []) if d.get("impact_severity") == "critical"
            ),
            "published_at": r.published_at.isoformat() if r.published_at else None,
        }
        for r in rows
    ]
