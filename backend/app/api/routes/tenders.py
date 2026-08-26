"""Tender management (admin create; all roles read)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.audit import append_audit
from app.db.session import get_db
from app.models.tender import Tender
from app.models.user import User
from app.schemas.schemas import TenderIn, TenderOut

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("", response_model=list[TenderOut])
def list_tenders(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Tender).order_by(Tender.id).all()


@router.get("/{tender_id}", response_model=TenderOut)
def get_tender(
    tender_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tender not found")
    return tender


@router.post("", response_model=TenderOut)
def create_tender(
    body: TenderIn,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    if db.query(Tender).filter(Tender.gem_ref == body.gem_ref).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "gem_ref already exists")
    tender = Tender(**body.model_dump())
    db.add(tender)
    db.commit()
    db.refresh(tender)
    append_audit(db, actor=f"user:{admin.id}", action="create_tender",
                 entity=f"tender:{tender.id}", payload={"gem_ref": tender.gem_ref})
    return tender