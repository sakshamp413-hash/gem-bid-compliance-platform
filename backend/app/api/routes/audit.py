"""Audit routes: hash-chained trail + integrity verification."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.audit import verify_chain
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.schemas import AuditEntryOut, AuditVerifyOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEntryOut])
def list_audit(
    entity: str | None = None,
    limit: int = 200,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if entity:
        q = q.filter(AuditLog.entity == entity)
    return q.order_by(AuditLog.seq.desc()).limit(min(limit, 500)).all()


@router.get("/verify", response_model=AuditVerifyOut)
def audit_integrity(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AuditVerifyOut(**verify_chain(db))