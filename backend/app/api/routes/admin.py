from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.permissions import Permission, ROLE_PERMISSIONS
from app.db.session import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogOut, UserOut

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/users", response_model=list[UserOut])
def users(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.USERS_MANAGE))):
    return db.scalars(select(User).order_by(User.department, User.full_name)).all()


@router.get("/roles")
def roles(_: User = Depends(require_permission(Permission.DASHBOARD_READ))):
    return [{"role": role, "permissions": sorted(list(perms))} for role, perms in ROLE_PERMISSIONS.items()]


@router.get("/audit", response_model=list[AuditLogOut])
def audit_logs(db: Session = Depends(get_db), _: User = Depends(require_permission(Permission.AUDIT_READ))):
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).all()
