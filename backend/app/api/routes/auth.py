from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    locked_until = user.locked_until if user else None
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    if user and locked_until and locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=429, detail="Tài khoản tạm khóa do đăng nhập sai nhiều lần")
    if not user or not verify_password(payload.password, user.hashed_password):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                user.failed_login_attempts = 0
            db.commit()
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khóa")
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    token = create_access_token(str(user.id), user.role)
    response.set_cookie(
        "vnpro_session", token, httponly=True, secure=settings.environment == "production",
        samesite="lax", max_age=settings.access_token_expire_minutes * 60, path="/",
    )
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie("vnpro_session", path="/")
