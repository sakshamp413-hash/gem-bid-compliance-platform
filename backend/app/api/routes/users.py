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