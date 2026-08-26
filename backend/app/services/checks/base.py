"""
Compliance check base contract.

Every check follows the pipeline:
    input → format/validity → portal cross-check → cross-document
    consistency → CheckOutput{result, confidence, evidence[], rule_ref}

Every piece of evidence references the exact source field/value/quote.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Evidence:
    """A single grounded piece of evidence for a finding."""

    doc_id: int | None = None
    doc_type: str | None = None
    field: str = ""
    value: str = ""
    quote: str | None = None
    source: str = "submission"  # document | portal | submission | rule
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "field": self.field,
            "value": self.value,
            "quote": self.quote,
            "source": self.source,
            "note": self.note,
        }


@dataclass
class CheckOutput:
    check_type: str
    result: str  # pass | fail | flag | na
    confidence: float = 1.0
    evidence: list[Evidence] = field(default_factory=list)
    rule_ref: str = ""
    portal_response: dict[str, Any] | None = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_type": self.check_type,
            "result": self.result,
            "confidence": round(self.confidence, 3),
            "evidence": [e.to_dict() for e in self.evidence],
            "rule_ref": self.rule_ref,
            "portal_response": self.portal_response,
            "summary": self.summary,
        }


class CheckContext(Protocol):
    """What every check receives. Filled by the pipeline service."""

    submission: Any
    tender: Any
    bidder: Any
    documents: dict[str, list[Any]]  # doc_type -> extracted dicts
    adapter: Any
    rules: Any


def add_evidence(
    output: CheckOutput,
    *,
    doc_id: int | None = None,
    doc_type: str | None = None,
    field: str,
    value: str,
    quote: str | None = None,
    source: str = "document",
    note: str = "",
) -> None:
    output.evidence.append(
        Evidence(
            doc_id=doc_id,
            doc_type=doc_type,
            field=field,
            value=value,
            quote=quote,
            source=source,
            note=note,
        )
    )


def check_registry() -> dict[str, Any]:
    """Map check_type -> module, imported lazily to avoid cycles."""
    from app.services import checks as _checks

    return {
        "udyam": _checks.check_udyam,
        "gst": _checks.check_gst,
        "pan": _checks.check_pan,
        "mca": _checks.check_mca,
        "local_content": _checks.check_local_content,
        "epfo": _checks.check_epfo,
        "esic": _checks.check_esic,
        "startup": _checks.check_startup,
        "nsic": _checks.check_nsic,
        "oem": _checks.check_oem,
        "digilocker": _checks.check_digilocker,
        "blacklist": _checks.check_blacklist,
    }