from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.response import ok
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginIn, RefreshIn, TokenOut, UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["01. Xác thực"])


@router.post("/login", summary="Đăng nhập")
def login(dto: LoginIn, db: Session = Depends(get_db)):
    tokens = AuthService(db).login(dto.username, dto.password)
    return ok(TokenOut(**tokens))


@router.post("/refresh", summary="Cấp lại access token")
def refresh(dto: RefreshIn, db: Session = Depends(get_db)):
    tokens = AuthService(db).refresh(dto.refresh_token)
    return ok(TokenOut(**tokens))


@router.post("/logout", summary="Đăng xuất")
def logout(_: User = Depends(get_current_user)):
    # Token JWT là stateless (không lưu ở server) nên không có gì để hủy ở đây —
    # chỉ báo cho client biết để tự xóa token đang lưu.
    return ok({"message": "Đã đăng xuất"})


@router.get("/me", summary="Thông tin người đang đăng nhập")
def me(user: User = Depends(get_current_user)):
    return ok(UserOut.model_validate(user))
