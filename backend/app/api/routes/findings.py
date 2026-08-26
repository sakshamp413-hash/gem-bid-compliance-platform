"""Cross-verification findings (AI evidence-linked) for a submission."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.cross_verify import run_cross_verify
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.bid_submission import BidSubmission
from app.models.document import Document
from app.models.tender import Tender
from app.models.bidder import Bidder
from app.models.user import User
from app.models.verification_check import VerificationCheck
from app.schemas.schemas import FindingsOut

router = APIRouter(prefix="/submissions/{submission_id}/findings", tags=["findings"])


@router.get("", response_model=FindingsOut)
def get_findings(
    submission_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = db.get(BidSubmission, submission_id)
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    tender = db.get(Tender, sub.tender_id)
    bidder = db.get(Bidder, sub.bidder_id)
    docs = db.query(Document).filter(Document.submission_id == sub.id).all()

    pack: dict[str, list[dict]] = {}
    for doc in docs:
        entry = dict(doc.extracted_json or {})
        entry["_doc_id"] = doc.id
        entry["_signature_status"] = doc.signature_status
        entry["_tamper_flags"] = doc.tamper_flags_json
        pack.setdefault(doc.doc_type, []).append(entry)

    checks = (
        db.query(VerificationCheck)
        .filter(VerificationCheck.submission_id == sub.id)
        .order_by(VerificationCheck.id)
        .all()
    )
    evidence = {
        "bidder": {"legal_name": bidder.legal_name, "entity_type": bidder.entity_type,
                   "pan": bidder.pan, "gstin": bidder.gstin,
                   "udyam_no": bidder.udyam_no, "cin": bidder.cin},
        "documents": pack,
        "portal": {},
        "checks": [{"check_type": c.check_type, "result": c.result,
                    "summary": (c.evidence_json or {}).get("summary", "")}
                   for c in checks],
    }
    result = run_cross_verify(evidence)
    return FindingsOut(**result)