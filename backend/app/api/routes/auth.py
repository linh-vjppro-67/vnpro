from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khóa")
    return TokenResponse(access_token=create_access_token(str(user.id), user.role), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
