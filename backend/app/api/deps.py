from collections.abc import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.permissions import has_permission
from app.db.session import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa đăng nhập")
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        user_id = int(payload.get("sub", "0"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không hoạt động")
    return user


def require_permission(permission: str) -> Callable:
    def checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền thực hiện thao tác này")
        return user
    return checker
