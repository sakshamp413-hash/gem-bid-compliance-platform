"""
Vendor Digital Twin endpoints (F03 + F04).

GET /vendors/{bidder_id}/readiness?tender_id=N  → readiness score + gap items
GET /vendors/{bidder_id}/remediation?submission_id=N → prioritised action plan
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("/{bidder_id}/readiness")
def vendor_readiness(
    bidder_id: int,
    tender_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compute (or return cached) Digital Twin readiness score + gap items
    for a (bidder, tender) pair.

    Returns {readiness_score, gap_items: [{requirement_id, label, status, severity}], computed_at}.
    """
    from app.models.bidder import Bidder
    from app.models.tender import Tender

    if db.get(Bidder, bidder_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bidder not found")
    if db.get(Tender, tender_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tender not found")

    from app.services.vendor_twin import compute_vendor_readiness

    return compute_vendor_readiness(db, bidder_id, tender_id)


@router.get("/{bidder_id}/remediation")
def vendor_remediation(
    bidder_id: int,
    submission_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate / return prioritised remediation tasks for a submission.
    Tasks are derived from failed/flagged verification checks.

    Returns list of [{label, severity, action, estimated_days, resolved}] sorted CRITICAL→LOW.
    """
    from app.models.bid_submission import BidSubmission

    sub = db.get(BidSubmission, submission_id)
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    if sub.bidder_id != bidder_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Submission does not belong to this bidder")

    from app.services.vendor_twin import compute_remediation_plan

    tasks = compute_remediation_plan(db, submission_id)
    return {
        "submission_id": submission_id,
        "bidder_id": bidder_id,
        "total_tasks": len(tasks),
        "critical_count": sum(1 for t in tasks if t["severity"] == "CRITICAL"),
        "tasks": tasks,
        "source_badge": "● DETERMINISTIC (rule-engine driven)",
    }
