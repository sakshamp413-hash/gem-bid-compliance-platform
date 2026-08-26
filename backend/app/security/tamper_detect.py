"""
PDF tamper / forgery detection (independent of signature validity).

Signals are split into HARD triggers (modification evidence) and SOFT
indicators (forensic notes that never alone mark a document tampered):

HARD (any one ⇒ `tampered=True`):
  1. signature no longer covers the content (intact=False)
  2. revisions appended AFTER the signing revision (revisions > 2)
  3. /ModDate later than the signature timestamp (metadata rewritten after signing)
  4. /ModDate ≠ /CreationDate on an UNSIGNED document
  5. producer string matches a re-processing/forgery fingerprint

SOFT (recorded in `details`/`soft_indicators` only — legitimate PDFs can
exhibit them):
  * object streams (normal in modern re-saved PDFs)
  * missing /CreationDate
  * unsigned document with multiple revisions

This avoids flagging legitimate documents (e.g. object-stream PDFs) while
still catching the seeded forgery with its three specific reasons.
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
      {tampered: bool, summary: str, reasons: list[str],
       soft_indicators: list[str], details: {...}}
    """
    path = Path(path)
    reasons: list[str] = []        # hard triggers
    soft: list[str] = []           # informational only
    details: dict[str, Any] = {}
    raw = path.read_bytes()

    # --- 1. revisions (incremental updates) ---
    n_revisions = raw.count(b"startxref")
    details["revisions"] = n_revisions

    sig = signature_report or {}
    signed = bool(sig.get("signed"))
    intact = bool(sig.get("intact"))

    if signed and not intact:
        reasons.append("signature no longer covers the document content (modified after signing)")
    if signed and n_revisions > 2:
        reasons.append(
            f"document has {n_revisions} revisions — content was updated AFTER the signing "
            "revision was appended"
        )
    if not signed and n_revisions > 1:
        soft.append(
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
            soft.append("document metadata carries no /CreationDate")

    # --- 5. producer fingerprint ---
    producer = str(pdfinfo.get("producer", "") or "")
    details["producer"] = producer
    if producer and any(k in producer.lower() for k in _FORGE_KEYWORDS):
        reasons.append(
            f"document producer '{producer}' matches a re-processing/forgery fingerprint"
        )

    # --- structural notes (soft only: object streams are normal in modern PDFs) ---
    try:
        import pikepdf

        with pikepdf.open(path) as pdf:
            details["object_count"] = len(pdf.objects)
            obj_streams = 0
            for obj in pdf.objects:
                try:
                    if obj is not None and obj.get("/Type") == pikepdf.Name("/ObjStm"):
                        obj_streams += 1
                except Exception:
                    pass
            details["object_streams"] = obj_streams
            if obj_streams > 0:
                soft.append(
                    f"file uses object streams ({obj_streams}) — "
                    "normal in modern re-saved PDFs (informational)"
                )
    except Exception as exc:
        details["pikepdf_error"] = str(exc)
        soft.append(f"structural analysis failed: {exc}")

    tampered = len(reasons) > 0
    return {
        "tampered": tampered,
        "summary": "; ".join(reasons) if reasons else "no tamper indicators detected",
        "reasons": reasons,
        "soft_indicators": soft,
        "details": details,
    }