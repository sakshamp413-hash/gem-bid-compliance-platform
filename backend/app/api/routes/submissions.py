"""Submissions: create (officer), list, detail, reassess."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.audit import append_audit
from app.db.session import get_db
from app.models.bidder import Bidder
from app.models.bid_submission import BidSubmission
from app.models.compliance_assessment import ComplianceAssessment
from app.models.document import Document
from app.models.officer_decision import OfficerDecision
from app.models.tender import Tender
from app.models.user import User
from app.models.verification_check import VerificationCheck
from app.schemas.schemas import (
    SubmissionCreate,
    SubmissionDetail,
    SubmissionOut,
)
from app.services.pipeline import run_verification

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.get("", response_model=list[SubmissionOut])
def list_submissions(
    tender_id: int | None = None,
    status_filter: str | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(BidSubmission)
    if tender_id:
        q = q.filter(BidSubmission.tender_id == tender_id)
    if status_filter:
        q = q.filter(BidSubmission.status == status_filter)
    subs = q.order_by(BidSubmission.id.desc()).all()
    out = []
    for s in subs:
        item = SubmissionOut.model_validate(s)
        item.tender = db.get(Tender, s.tender_id)
        item.bidder = db.get(Bidder, s.bidder_id)
        item.assessment = (
            db.query(ComplianceAssessment)
            .filter(ComplianceAssessment.submission_id == s.id)
            .order_by(ComplianceAssessment.id.desc())
            .first()
        )
        out.append(item)
    return out


@router.post("", response_model=SubmissionOut)
def create_submission(
    body: SubmissionCreate,
    user: User = Depends(require_roles("officer", "admin")),
    db: Session = Depends(get_db),
):
    tender = db.get(Tender, body.tender_id)
    if tender is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tender not found")
    bidder = Bidder(**body.bidder.model_dump())
    db.add(bidder)
    db.flush()
    sub = BidSubmission(tender_id=tender.id, bidder_id=bidder.id)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    append_audit(db, actor=f"user:{user.id}", action="create_submission",
                 entity=f"submission:{sub.id}",
                 payload={"tender_id": tender.id, "bidder": bidder.legal_name})
    return SubmissionOut.model_validate(sub)


@router.get("/{submission_id}", response_model=SubmissionDetail)
def get_submission(
    submission_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = db.get(BidSubmission, submission_id)
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    detail = SubmissionDetail.model_validate(sub)
    detail.tender = db.get(Tender, sub.tender_id)
    detail.bidder = db.get(Bidder, sub.bidder_id)
    detail.documents = (
        db.query(Document).filter(Document.submission_id == sub.id).all()
    )
    detail.checks = (
        db.query(VerificationCheck)
        .filter(VerificationCheck.submission_id == sub.id)
        .order_by(VerificationCheck.id)
        .all()
    )
    detail.assessment = (
        db.query(ComplianceAssessment)
        .filter(ComplianceAssessment.submission_id == sub.id)
        .order_by(ComplianceAssessment.id.desc())
        .first()
    )
    detail.decisions = (
        db.query(OfficerDecision)
        .filter(OfficerDecision.submission_id == sub.id)
        .order_by(OfficerDecision.id)
        .all()
    )
    # findings surfaced from assessment model meta? recompute deterministically
    if detail.assessment and detail.assessment.model_meta_json:
        pass
    return detail


@router.post("/{submission_id}/assess", response_model=SubmissionDetail)
def assess_submission(
    submission_id: int,
    user: User = Depends(require_roles("officer", "admin")),
    db: Session = Depends(get_db),
):
    sub = db.get(BidSubmission, submission_id)
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    run_verification(db, sub, actor=f"user:{user.id}")
    return get_submission(submission_id, user, db)