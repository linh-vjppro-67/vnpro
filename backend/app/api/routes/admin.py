from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.permissions import Permission, ROLE_PERMISSIONS
from app.db.session import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogOut, UserOut
from app.services import audit

router = APIRouter(prefix="/admin", tags=["Administration"])


class UserActiveUpdate(BaseModel):
    is_active: bool


@router.get("/users", response_model=list[UserOut])
def users(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.USERS_MANAGE))):
    return db.scalars(select(User).order_by(User.department, User.full_name)).all()


@router.patch("/users/{user_id}/active", response_model=UserOut)
def update_user_active(
    user_id: int,
    payload: UserActiveUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USERS_MANAGE)),
):
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(404, "Không tìm thấy tài khoản")
    if item.id == current_user.id and not payload.is_active:
        raise HTTPException(409, "Bạn không thể tự khóa tài khoản đang đăng nhập")
    if item.role == "SYSTEM_ADMIN" and item.is_active and not payload.is_active:
        active_admins = db.scalar(select(User.id).where(User.role == "SYSTEM_ADMIN", User.is_active, User.id != item.id).limit(1))
        if not active_admins:
            raise HTTPException(409, "Không thể khóa quản trị viên hoạt động cuối cùng")
    if item.is_active == payload.is_active:
        return item
    item.is_active = payload.is_active
    action = "UNLOCK_USER" if payload.is_active else "LOCK_USER"
    audit(db, current_user, action, "USER", item.id, item.email)
    db.commit(); db.refresh(item)
    return item


@router.get("/roles")
def roles(_: User = Depends(require_permission(Permission.DASHBOARD_READ))):
    return [{"role": role, "permissions": sorted(list(perms))} for role, perms in ROLE_PERMISSIONS.items()]


@router.get("/audit", response_model=list[AuditLogOut])
def audit_logs(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.AUDIT_READ))):
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).all()
