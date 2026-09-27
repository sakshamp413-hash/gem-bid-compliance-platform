"""
Tender Requirement Compiler (F01) — parses an ATC/tender PDF into structured
JSON rule objects using pdfplumber + regex anchors.

compile_tender_requirements(text: str) -> list[CompiledRequirement]

Each CompiledRequirement is a structured dict with:
  {id, label, category, raw_clause, threshold_value, threshold_unit,
   doc_required, severity, rule_ref}
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── category anchors ────────────────────────────────────────────────────────
_CAT_PATTERNS: list[tuple[str, str]] = [
    ("msme", r"\bmsme\b|micro\s+(?:and\s+)?small|udyam"),
    ("startup", r"startup\s+india|dipp\s+recognition"),
    ("nsic", r"\bnsic\b|national\s+small\s+industries"),
    ("local_content", r"local\s+content|make\s+in\s+india|domestic\s+content"),
    ("security_deposit", r"earnest\s+money\s+deposit|\bemd\b|security\s+deposit|bid\s+security"),
    ("blacklist", r"blacklist|debarr|ban(?:ned)?|insolvent|integrity\s+pact"),
    ("gst", r"gstin|gst\s+registration"),
    ("pan", r"\bpan\b|permanent\s+account\s+number"),
    ("epfo", r"\bepfo\b|employees?\s+provident\s+fund"),
    ("esic", r"\besic\b|employees?\s+state\s+insurance"),
    ("oem_auth", r"oem\s+authoris[sz]ation|manufacturer\s+authoris[sz]ation"),
    ("experience", r"(?:prior|past|minimum)\s+experience|years\s+of\s+experience"),
    ("turnover", r"(?:annual\s+)?(?:average\s+)?turnover"),
    ("document", r"document|certificate|proof|affidavit"),
]

_AMOUNT_RE = re.compile(
    r"(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*"
    r"(?:crore|cr|lakh|lac|lakhs|thousand|k)?\b",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"([\d.]+)\s*%")
_YEARS_RE = re.compile(r"(\d+)\s*(?:financial\s+)?years?")
_CLAUSE_SPLIT_RE = re.compile(
    r"(?:^|\n)(?:\d+[\.\)]\s+|[a-z][\.\)]\s+|[ivx]+[\.\)]\s+|\(?\w+\)\s+|•\s+)",
    re.MULTILINE | re.IGNORECASE,
)

_SEVERITY_MAP: dict[str, str] = {
    "turnover": "critical",
    "msme": "high",
    "experience": "high",
    "local_content": "critical",
    "security_deposit": "critical",
    "blacklist": "critical",
    "gst": "high",
    "pan": "high",
    "epfo": "medium",
    "esic": "medium",
    "oem_auth": "high",
    "startup": "medium",
    "nsic": "medium",
    "document": "medium",
}


@dataclass
class CompiledRequirement:
    id: str                          # e.g. "REQ-001"
    label: str                       # short human label
    category: str                    # turnover|msme|experience|…
    raw_clause: str                  # verbatim text slice
    threshold_value: str | None      # numeric/textual threshold
    threshold_unit: str | None       # crore|%|years|None
    doc_required: str | None         # suggested document type
    severity: str                    # critical|high|medium|low
    rule_ref: str                    # COMPILE/<category>/<seq>
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_DOC_MAP: dict[str, str] = {
    "turnover": "financial_statement",
    "msme": "udyam",
    "gst": "gst_cert",
    "pan": "pan_card",
    "experience": "work_order",
    "local_content": "local_content",
    "security_deposit": "emd_receipt",
    "epfo": "epfo",
    "esic": "esic",
    "oem_auth": "oem_auth",
    "startup": "startup",
    "nsic": "nsic",
    "blacklist": "self_declaration",
    "document": None,
}


def _detect_category(clause: str) -> str:
    low = clause.lower()
    for cat, pattern in _CAT_PATTERNS:
        if re.search(pattern, low):
            return cat
    return "document"


def _extract_threshold(clause: str) -> tuple[str | None, str | None]:
    """Return (value, unit) pair from a clause string."""
    low = clause.lower()
    # percentage
    m = _PERCENT_RE.search(clause)
    if m:
        return m.group(1), "%"
    # years
    m = _YEARS_RE.search(low)
    if m:
        return m.group(1), "years"
    # monetary
    m = _AMOUNT_RE.search(clause)
    if m:
        raw_val = m.group(0).strip()
        unit = None
        for u in ("crore", "cr", "lakh", "lac", "lakhs", "thousand", "k"):
            if u in raw_val.lower():
                unit = u
                break
        return m.group(1).replace(",", ""), unit or "INR"
    return None, None


def _split_clauses(text: str) -> list[str]:
    """Split tender text into discrete clauses for processing."""
    parts = _CLAUSE_SPLIT_RE.split(text)
    clauses = []
    for part in parts:
        part = part.strip()
        if len(part) > 30:          # ignore very short fragments
            clauses.append(part)
    if not clauses:
        # fallback: split by double newline
        clauses = [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) > 30]
    return clauses


def compile_tender_requirements(text: str) -> list[CompiledRequirement]:
    """
    Parse tender/ATC PDF text into structured CompiledRequirement objects.

    Args:
        text: full extracted text from the tender PDF

    Returns:
        list of CompiledRequirement (sorted critical → low)
    """
    clauses = _split_clauses(text)
    results: list[CompiledRequirement] = []
    seq_by_cat: dict[str, int] = {}

    for clause in clauses:
        cat = _detect_category(clause)
        seq = seq_by_cat.get(cat, 0) + 1
        seq_by_cat[cat] = seq

        threshold_val, threshold_unit = _extract_threshold(clause)
        label_words = clause.split()[:8]
        label = " ".join(label_words).rstrip(".,;:") + ("…" if len(clause.split()) > 8 else "")

        req = CompiledRequirement(
            id=f"REQ-{len(results) + 1:03d}",
            label=label,
            category=cat,
            raw_clause=clause[:500],
            threshold_value=threshold_val,
            threshold_unit=threshold_unit,
            doc_required=_DOC_MAP.get(cat),
            severity=_SEVERITY_MAP.get(cat, "low"),
            rule_ref=f"COMPILE/{cat.upper()}/{seq:03d}",
        )
        results.append(req)

    _SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    results.sort(key=lambda r: _SEV_ORDER.get(r.severity, 4))
    logger.info("compiled %d requirements from %d chars of tender text", len(results), len(text))
    return results
