"""Admin: rule-set editing (rules are data), dashboard stats."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.audit import append_audit
from app.db.session import SessionLocal, get_db
from app.models.bid_submission import BidSubmission
from app.models.compliance_assessment import ComplianceAssessment
from app.models.tender import Tender
from app.models.user import User
from app.rules.engine import get_rule_store
from app.schemas.schemas import MessageOut, RuleSetOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/rules", response_model=RuleSetOut)
def get_rules(_: User = Depends(require_roles("admin", "auditor"))):
    store = get_rule_store()
    return RuleSetOut(data=store.current.data, file=str(store.path))


@router.put("/rules", response_model=RuleSetOut)
def update_rules(
    body: dict,
    admin: User = Depends(require_roles("admin")),
):
    store = get_rule_store()
    if not isinstance(body, dict) or "weights" not in body:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "rule payload must include 'weights'")
    rs = store.save(body)
    with SessionLocal() as audit_db:
        append_audit(audit_db, actor=f"user:{admin.id}", action="update_rules",
                     entity="rules", payload={"keys": sorted(body.keys())})
    return RuleSetOut(data=rs.data, file=str(store.path))


@router.post("/rules/reload", response_model=RuleSetOut)
def reload_rules(admin: User = Depends(require_roles("admin"))):
    store = get_rule_store()
    rs = store.reload()
    with SessionLocal() as audit_db:
        append_audit(audit_db, actor=f"user:{admin.id}", action="reload_rules", entity="rules")
    return RuleSetOut(data=rs.data, file=str(store.path))


@router.get("/stats")
def dashboard_stats(_: User = Depends(require_roles("officer", "admin", "auditor")),
                    db: Session = Depends(get_db)):
    total_tenders = db.query(func.count(Tender.id)).scalar() or 0
    total_subs = db.query(func.count(BidSubmission.id)).scalar() or 0
    risk_dist = dict(
        db.query(ComplianceAssessment.risk_level, func.count(ComplianceAssessment.id))
        .group_by(ComplianceAssessment.risk_level).all()
    )
    status_dist = dict(
        db.query(BidSubmission.status, func.count(BidSubmission.id))
        .group_by(BidSubmission.status).all()
    )
    avg_score = db.query(func.avg(ComplianceAssessment.score)).scalar() or 0
    return {
        "tenders": total_tenders,
        "submissions": total_subs,
        "avg_score": round(float(avg_score), 1),
        "risk_distribution": {k: v for k, v in sorted(risk_dist.items())},
        "status_distribution": {k: v for k, v in sorted(status_dist.items())},
    }