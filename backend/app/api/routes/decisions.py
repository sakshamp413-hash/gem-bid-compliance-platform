"""Officer decision flow (human-in-the-loop)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.audit import append_audit
from app.db.session import get_db
from app.models.bid_submission import BidSubmission
from app.models.compliance_assessment import ComplianceAssessment
from app.models.officer_decision import OfficerDecision
from app.models.user import User
from app.schemas.schemas import DecisionCreate, DecisionOut, MessageOut

router = APIRouter(prefix="/submissions/{submission_id}/decisions", tags=["decisions"])


@router.post("", response_model=DecisionOut)
def record_decision(
    submission_id: int,
    body: DecisionCreate,
    user: User = Depends(require_roles("officer", "admin")),
    db: Session = Depends(get_db),
):
    sub = db.get(BidSubmission, submission_id)
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")

    assessment = (
        db.query(ComplianceAssessment)
        .filter(ComplianceAssessment.submission_id == submission_id)
        .order_by(ComplianceAssessment.id.desc())
        .first()
    )
    overrides = False
    if assessment and assessment.recommendation_action:
        rec_map = {
            "qualify": "qualify",
            "needs_review": "escalate",
            "disqualify_candidate": "disqualify",
        }
        recommended = rec_map.get(assessment.recommendation_action)
        overrides = recommended != body.decision and body.decision in ("qualify", "disqualify")

    decision = OfficerDecision(
        submission_id=submission_id,
        officer_id=user.id,
        decision=body.decision,
        overrides_recommendation=overrides,
        justification=body.justification,
    )
    db.add(decision)
    status_map = {
        "qualify": "accepted",
        "disqualify": "rejected",
        "request_docs": "requested_docs",
        "escalate": "under_review",
    }
    sub.status = status_map.get(body.decision, sub.status)
    db.commit()
    db.refresh(decision)

    append_audit(
        db,
        actor=f"user:{user.id}",
        action="officer_decision",
        entity=f"submission:{submission_id}",
        payload={
            "decision": body.decision,
            "overrides": overrides,
            "justification_hash": __import__("hashlib").sha256(body.justification.encode()).hexdigest()[:16],
        },
    )
    return decision


@router.get("", response_model=list[DecisionOut])
def list_decisions(
    submission_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(OfficerDecision)
        .filter(OfficerDecision.submission_id == submission_id)
        .order_by(OfficerDecision.id)
        .all()
    )


@router.post("/request-document", response_model=MessageOut)
def request_document(
    submission_id: int,
    body: DecisionCreate,
    user: User = Depends(require_roles("officer", "admin")),
    db: Session = Depends(get_db),
):
    """Officer requests an additional document from the bidder (audited)."""
    decision = record_decision(submission_id, body, user, db)
    append_audit(db, actor=f"user:{user.id}", action="request_document",
                 entity=f"submission:{submission_id}",
                 payload={"note": "document requested from bidder"})
    return MessageOut(message=f"Document requested (decision #{decision.id})")