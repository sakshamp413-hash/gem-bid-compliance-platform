"""User management (admin only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.audit import append_audit
from app.db.session import get_db
from app.models.user import User
from app.schemas.schemas import MessageOut, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

# Capability matrix — single source of truth for both backend enforcement and frontend UI
ROLE_CAPABILITIES: dict[str, dict[str, bool]] = {
    "officer": {
        "tender_ingestion": True,
        "bid_evidence_review": True,
        "compliance_score": True,
        "risk_fraud_indicators": True,
        "rule_visibility": True,
        "procurement_decision": True,
        "decision_override": True,
        "audit_verification": True,
        "rule_drafting": False,
        "rule_publishing": False,
        "user_management": False,
        "integration_management": False,
    },
    "auditor": {
        "tender_ingestion": False,       # 👁 read-only — enforced in UI (no create button)
        "bid_evidence_review": True,     # 👁 read-only — no re-assess or upload buttons
        "compliance_score": True,
        "risk_fraud_indicators": True,
        "rule_visibility": True,
        "procurement_decision": False,
        "decision_override": False,
        "audit_verification": True,
        "rule_drafting": False,
        "rule_publishing": False,
        "user_management": False,
        "integration_management": False,
    },
    "admin": {
        "tender_ingestion": True,
        "bid_evidence_review": True,     # 👁 read-only by convention — decision is flagged ⚠️
        "compliance_score": True,
        "risk_fraud_indicators": True,
        "rule_visibility": True,
        "procurement_decision": True,    # ⚠️ flagged as admin_decision_override in audit
        "decision_override": True,       # ⚠️ flagged as admin_decision_override in audit
        "audit_verification": True,
        "rule_drafting": True,
        "rule_publishing": True,         # * requires PUT /admin/rules (admin only)
        "user_management": True,
        "integration_management": True,
    },
}


@router.get("/me/permissions")
def get_my_permissions(user: User = Depends(get_current_user)):
    """Return the RBAC capability map for the logged-in user's role."""
    caps = ROLE_CAPABILITIES.get(user.role, {})
    return {"role": user.role, "capabilities": caps}


@router.get("", response_model=list[UserOut])
def list_users(
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut)
def create_user(
    body: UserCreate,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User.create(body.name, body.email.lower(), body.role, body.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    append_audit(db, actor=f"user:{admin.id}", action="create_user",
                 entity=f"user:{user.id}", payload={"role": user.role})
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    append_audit(db, actor=f"user:{admin.id}", action="update_user",
                 entity=f"user:{user.id}",
                 payload={k: v for k, v in body.model_dump().items() if v is not None})
    return UserOut.model_validate(user)


@router.delete("/{user_id}", response_model=MessageOut)
def delete_user(
    user_id: int,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete yourself")
    db.delete(user)
    db.commit()
    append_audit(db, actor=f"user:{admin.id}", action="delete_user", entity=f"user:{user_id}")
    return MessageOut(message="User deleted")