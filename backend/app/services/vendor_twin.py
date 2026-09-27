"""
Vendor Digital Twin (F03) + Bid Readiness Remediation Engine (F04)

Given a bidder + tender, computes:
  - readiness_score (0-100)
  - gap_items: per-requirement status (met | gap | unknown)
  - remediation_tasks: prioritised action list (CRITICAL→LOW)

Deterministic, fully offline, no external API calls needed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)

_SEVERITY_SCORE: dict[str, float] = {
    "CRITICAL": 30.0,
    "HIGH": 15.0,
    "MEDIUM": 7.0,
    "LOW": 3.0,
}

_REMEDIATION_ACTIONS: dict[str, dict[str, Any]] = {
    "udyam": {
        "label": "Udyam Registration (MSME Certificate)",
        "action": "Register at udyamregistration.gov.in. Processing: 1-3 business days. Requires Aadhaar + PAN.",
        "severity": "HIGH",
        "estimated_days": 3,
    },
    "gst": {
        "label": "GST Registration Certificate",
        "action": "Apply at gst.gov.in. If already registered, download GSTIN certificate from GST portal.",
        "severity": "HIGH",
        "estimated_days": 5,
    },
    "pan": {
        "label": "PAN Card",
        "action": "Apply at incometaxindiaefiling.gov.in or use Aadhaar-based instant PAN. Processing: 1-7 days.",
        "severity": "HIGH",
        "estimated_days": 7,
    },
    "epfo": {
        "label": "EPFO Registration (Provident Fund)",
        "action": "Register at epfindia.gov.in if you have 20+ employees. Obtain PF code certificate.",
        "severity": "MEDIUM",
        "estimated_days": 10,
    },
    "esic": {
        "label": "ESIC Registration",
        "action": "Register at esic.in if you have 10+ employees. Obtain ESIC code certificate.",
        "severity": "MEDIUM",
        "estimated_days": 10,
    },
    "local_content": {
        "label": "Local Content Certificate",
        "action": "Self-certify local content % per MII Order 2017 format. Get CA certification if >20 Cr order.",
        "severity": "CRITICAL",
        "estimated_days": 14,
    },
    "oem_auth": {
        "label": "OEM Authorization Letter",
        "action": "Obtain authorization on OEM letterhead: product scope, validity ≥ bid validity, signatory name + seal.",
        "severity": "HIGH",
        "estimated_days": 7,
    },
    "blacklist": {
        "label": "Non-Blacklist Self-Declaration",
        "action": "Prepare self-declaration affidavit on Rs 100 stamp paper stating non-debarment from all govt portals.",
        "severity": "CRITICAL",
        "estimated_days": 2,
    },
    "startup": {
        "label": "Startup India Recognition",
        "action": "Apply at startupindia.gov.in. Requires DIPP recognition. Valid certificate needed.",
        "severity": "MEDIUM",
        "estimated_days": 30,
    },
    "nsic": {
        "label": "NSIC Registration Certificate",
        "action": "Register via nsic.co.in for MSME procurement benefits. Requires financial assessment.",
        "severity": "MEDIUM",
        "estimated_days": 45,
    },
    "turnover": {
        "label": "Annual Turnover Threshold",
        "action": "Provide audited P&L / Balance Sheet for last 3 FYs. If turnover is below threshold, consider consortium bidding.",
        "severity": "CRITICAL",
        "estimated_days": 7,
    },
    "experience": {
        "label": "Prior Experience / Work Orders",
        "action": "Compile work order copies + completion certificates for similar supply/service contracts.",
        "severity": "HIGH",
        "estimated_days": 5,
    },
    "security_deposit": {
        "label": "Earnest Money Deposit (EMD)",
        "action": "Arrange EMD via bank guarantee or DD as per tender requirement before bid submission deadline.",
        "severity": "CRITICAL",
        "estimated_days": 3,
    },
}


@dataclass
class GapItem:
    requirement_id: str
    label: str
    status: str      # met | gap | unknown
    severity: str    # CRITICAL | HIGH | MEDIUM | LOW
    doc_required: str | None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RemediationAction:
    requirement_id: str
    label: str
    severity: str
    action: str
    estimated_days: int | None
    rule_ref: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _has_value(bidder, attr: str) -> bool:
    val = getattr(bidder, attr, None)
    return bool(val and str(val).strip())


def _check_requirement(bidder, tender, req_key: str) -> str:
    """Return 'met' | 'gap' | 'unknown' for a given requirement key."""
    if req_key == "udyam":
        return "met" if _has_value(bidder, "udyam_no") else "gap"
    if req_key == "gst":
        return "met" if _has_value(bidder, "gstin") else "gap"
    if req_key == "pan":
        return "met" if _has_value(bidder, "pan") else "gap"
    if req_key == "epfo":
        return "met" if _has_value(bidder, "epfo_no") else "gap"
    if req_key == "esic":
        return "met" if _has_value(bidder, "esic_no") else "gap"
    if req_key == "startup":
        return "met" if _has_value(bidder, "startup_no") else "gap"
    if req_key == "nsic":
        return "met" if _has_value(bidder, "nsic_no") else "gap"
    if req_key == "oem_auth":
        # resellers need OEM auth
        return "unknown" if getattr(bidder, "is_reseller", True) else "met"
    if req_key == "local_content":
        return "unknown" if getattr(tender, "local_content_class_required", None) else "met"
    if req_key == "blacklist":
        # always flag as unknown (requires manual confirmation)
        return "unknown"
    if req_key == "turnover":
        min_t = getattr(tender, "min_turnover_crore", None)
        if min_t is None:
            return "met"
        return "unknown"  # actual turnover not stored on bidder; officer must verify
    if req_key == "msme":
        if getattr(tender, "msme_only", False):
            return "met" if _has_value(bidder, "udyam_no") else "gap"
        return "met"
    if req_key == "security_deposit":
        return "unknown"  # EMD status not tracked at bidder level
    if req_key == "experience":
        return "unknown"
    return "unknown"


def _applicable_requirements(tender) -> list[str]:
    """Return list of requirement keys applicable to this tender."""
    reqs = ["pan", "gst", "blacklist"]
    if getattr(tender, "msme_only", False):
        reqs.append("msme")
    if getattr(tender, "local_content_class_required", None) not in (None, "None", "none"):
        reqs.append("local_content")
    if getattr(tender, "min_turnover_crore", None):
        reqs.append("turnover")
    # always required for standard tenders
    reqs += ["security_deposit", "experience"]
    # optional registrations — check if in required_docs
    required_docs = getattr(tender, "required_docs_json", []) or []
    for key in ("epfo", "esic", "startup", "nsic", "udyam", "oem_auth"):
        if key in required_docs:
            reqs.append(key)
    return list(dict.fromkeys(reqs))  # deduplicate, preserve order


def compute_vendor_readiness(
    db: Session, bidder_id: int, tender_id: int
) -> dict[str, Any]:
    """
    Compute Digital Twin readiness score + gap items for a (bidder, tender) pair.
    Caches result in VendorReadinessCache.
    Returns: {readiness_score, gap_items, computed_at, cached}
    """
    from app.models.bidder import Bidder
    from app.models.tender import Tender
    from app.models.vendor_readiness_cache import VendorReadinessCache

    bidder = db.get(Bidder, bidder_id)
    tender = db.get(Tender, tender_id)
    if bidder is None or tender is None:
        return {"readiness_score": 0.0, "gap_items": [], "computed_at": datetime.utcnow().isoformat(), "cached": False}

    req_keys = _applicable_requirements(tender)
    gap_items: list[GapItem] = []
    penalty = 0.0
    max_penalty = sum(_SEVERITY_SCORE.get(
        _REMEDIATION_ACTIONS.get(k, {}).get("severity", "LOW"), 3.0
    ) for k in req_keys)

    for key in req_keys:
        status = _check_requirement(bidder, tender, key)
        meta = _REMEDIATION_ACTIONS.get(key, {"label": key, "severity": "LOW"})
        gap = GapItem(
            requirement_id=key,
            label=meta["label"],
            status=status,
            severity=meta.get("severity", "LOW"),
            doc_required=key if key in ("udyam", "gst", "pan", "epfo", "esic",
                                        "startup", "nsic", "oem_auth", "local_content") else None,
        )
        gap_items.append(gap)
        if status == "gap":
            penalty += _SEVERITY_SCORE.get(meta.get("severity", "LOW"), 3.0)
        elif status == "unknown":
            penalty += _SEVERITY_SCORE.get(meta.get("severity", "LOW"), 3.0) * 0.4

    readiness = max(0.0, 100.0 - (penalty / max(max_penalty, 1) * 100.0)) if max_penalty else 100.0
    readiness = round(readiness, 1)

    gap_dicts = [g.to_dict() for g in gap_items]
    now = datetime.utcnow()

    # upsert cache
    cache = (
        db.query(VendorReadinessCache)
        .filter(
            VendorReadinessCache.bidder_id == bidder_id,
            VendorReadinessCache.tender_id == tender_id,
        )
        .first()
    )
    if cache:
        cache.readiness_score = readiness
        cache.gap_items = gap_dicts
        cache.computed_at = now
    else:
        cache = VendorReadinessCache(
            bidder_id=bidder_id,
            tender_id=tender_id,
            readiness_score=readiness,
            gap_items=gap_dicts,
            computed_at=now,
        )
        db.add(cache)
    db.commit()

    return {
        "readiness_score": readiness,
        "gap_items": gap_dicts,
        "computed_at": now.isoformat(),
        "cached": False,
    }


def compute_remediation_plan(
    db: Session, submission_id: int
) -> list[dict[str, Any]]:
    """
    Generate prioritised remediation tasks for a submission based on
    failed/flagged verification checks.
    Persists RemediationTask rows and returns them as dicts.
    """
    from app.models.bid_submission import BidSubmission
    from app.models.remediation_task import RemediationTask
    from app.models.verification_check import VerificationCheck

    sub = db.get(BidSubmission, submission_id)
    if sub is None:
        return []

    checks = (
        db.query(VerificationCheck)
        .filter(VerificationCheck.submission_id == submission_id)
        .all()
    )

    # clear old tasks
    db.query(RemediationTask).filter(
        RemediationTask.submission_id == submission_id
    ).delete()
    db.commit()

    _SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    tasks: list[RemediationTask] = []

    for check in checks:
        if check.result in ("pass", "na"):
            continue
        key = check.check_type
        meta = _REMEDIATION_ACTIONS.get(key, {
            "label": key.replace("_", " ").title(),
            "action": f"Resolve {key} compliance gap. Contact procurement officer for guidance.",
            "severity": "MEDIUM",
            "estimated_days": None,
        })
        task = RemediationTask(
            submission_id=submission_id,
            requirement_id=key,
            label=meta["label"],
            severity=meta.get("severity", "MEDIUM"),
            action=meta["action"],
            estimated_days=meta.get("estimated_days"),
            resolved=False,
        )
        tasks.append(task)
        db.add(task)

    db.commit()
    tasks.sort(key=lambda t: _SEV_ORDER.get(t.severity, 4))
    logger.info("remediation plan: %d tasks for submission %s", len(tasks), submission_id)
    return [
        {
            "id": t.id,
            "submission_id": t.submission_id,
            "requirement_id": t.requirement_id,
            "label": t.label,
            "severity": t.severity,
            "action": t.action,
            "estimated_days": t.estimated_days,
            "resolved": t.resolved,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]
