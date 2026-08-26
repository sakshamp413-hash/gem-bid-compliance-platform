"""
PDF tamper / forgery detection (independent of signature validity).

Signals analyzed (signature-aware — legitimate signing itself appends a
revision and updates /ModDate, so comparisons are made against the
signature's own recorded timestamp):

  1. revisions > 2                       → updates AFTER the signing revision
  2. revisions > 1 with no valid sig     → rewritten after creation
  3. /ModDate later than signature time  → metadata rewritten after signing
  4. /ModDate vs /CreationDate mismatch  → (unsigned docs) metadata rewritten
  5. Producer string anomalies           → re-saved/forged-tool fingerprints
  6. object-stream usage                 → re-processed file fingerprint

Output: human-readable reasons + details, aggregated `tampered` boolean.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_FORGE_KEYWORDS = ("re-signed", "forge", "fake", "edit", "tamper", "re-created", "screenshot")


def _parse_pdf_datetime(value: str | None) -> datetime | None:
    """Parse a PDF date (D:YYYYMMDDHHMMSS+HH'MM') or ISO-8601 to UTC datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass
    m = re.search(
        r"D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?"
        r"(?:([+-])(\d{2})'(\d{2})'?|Z)?",
        value,
    )
    if not m:
        return None
    parts = [int(x) if x else 0 for x in m.groups()[:6]]
    year, month, day, hour, minute, second = parts
    try:
        dt_naive = datetime(year, month or 1, day or 1, hour, minute, second)
    except ValueError:
        return None
    sign = m.group(7)
    if sign:
        off_h, off_m = int(m.group(8) or 0), int(m.group(9) or 0)
        delta = timedelta(hours=off_h, minutes=off_m)
        dt_naive = dt_naive - delta if sign == "+" else dt_naive + delta
    return dt_naive.replace(tzinfo=timezone.utc)


def _extract_text_layer_heuristics(path: str | Path) -> dict[str, Any]:
    """Producer/metadata/font info via pdfplumber if available."""
    import pdfplumber

    try:
        with pdfplumber.open(path) as pdf:
            info = pdf.metadata or {}
            fonts: set[str] = set()
            for page in pdf.pages[:3]:
                for char in page.chars[:200]:
                    if char.get("fontname"):
                        fonts.add(str(char["fontname"]))
            return {
                "producer": str(info.get("Producer", "") or ""),
                "creation_date": str(info.get("CreationDate", "") or ""),
                "mod_date": str(info.get("ModDate", "") or ""),
                "fonts": sorted(fonts)[:12],
            }
    except Exception as exc:
        return {"error": str(exc)}


def analyze_pdf_tamper(path: str | Path, signature_report: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Returns:
      {tampered: bool, summary: str, reasons: list[str], details: {...}}
    """
    path = Path(path)
    reasons: list[str] = []
    details: dict[str, Any] = {}
    raw = path.read_bytes()

    # --- 1. revisions (incremental updates) ---
    n_revisions = raw.count(b"startxref")
    details["revisions"] = n_revisions

    sig = signature_report or {}
    signed = bool(sig.get("signed"))
    intact = bool(sig.get("intact"))

    if signed and n_revisions > 2:
        reasons.append(
            f"document has {n_revisions} revisions — content was updated AFTER the signing "
            "revision was appended"
        )
    if signed and not intact and n_revisions > 1:
        reasons.append("signature no longer covers the document content (modified after signing)")
    if not signed and n_revisions > 1:
        reasons.append(
            f"unsigned document has {n_revisions} revisions (incremental updates after creation)"
        )

    # --- 2/3/4. metadata timing ---
    pdfinfo = _extract_text_layer_heuristics(path)
    details["pdfinfo"] = pdfinfo
    if "error" not in pdfinfo:
        creation = pdfinfo.get("creation_date", "")
        mod = pdfinfo.get("mod_date", "")
        details["creation_date"] = creation
        details["mod_date"] = mod

        sig_time = _parse_pdf_datetime(sig.get("sig_timestamp") or "")
        mod_dt = _parse_pdf_datetime(mod)
        creation_dt = _parse_pdf_datetime(creation)

        if signed and mod_dt and sig_time:
            # tolerance: signing writes /ModDate within seconds of the sig M;
            # a forge rewrites it by days. 5-minute tolerance kills the race.
            if mod_dt > sig_time + timedelta(minutes=5):
                reasons.append(
                    f"/ModDate ({mod}) is LATER than the signature timestamp "
                    f"({sig_time.isoformat()}) — metadata was rewritten after signing"
                )
        if not signed and mod_dt and creation_dt and mod_dt != creation_dt:
            reasons.append(
                f"/ModDate ({mod}) differs from /CreationDate ({creation}) — "
                "metadata rewritten after creation"
            )
        if not creation:
            reasons.append("document metadata carries no /CreationDate")

    # --- 5. producer fingerprint ---
    producer = str(pdfinfo.get("producer", "") or "")
    details["producer"] = producer
    if producer and any(k in producer.lower() for k in _FORGE_KEYWORDS):
        reasons.append(
            f"document producer '{producer}' matches a re-processing/forgery fingerprint"
        )

    # --- 6. structural anomalies via pikepdf ---
    try:
        import pikepdf

        with pikepdf.open(path) as pdf:
            details["object_count"] = len(pdf.objects)
            obj_streams = 0
            for obj in pdf.objects:
                try:
                    if obj is not None and obj.type_name == "/ObjStm":
                        obj_streams += 1
                except Exception:
                    pass
            details["object_streams"] = obj_streams
            if obj_streams > 0:
                reasons.append(
                    f"file uses object streams ({obj_streams}) — typical of re-saved/processed files"
                )
    except Exception as exc:
        details["pikepdf_error"] = str(exc)
        reasons.append(f"structural analysis failed: {exc}")

    tampered = len(reasons) > 0
    return {
        "tampered": tampered,
        "summary": "; ".join(reasons) if reasons else "no tamper indicators detected",
        "reasons": reasons,
        "details": details,
    }