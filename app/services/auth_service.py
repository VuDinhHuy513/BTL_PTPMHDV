"""Đăng nhập, cấp token, quản lý tài khoản."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.security import (create_access_token, create_refresh_token,
                               decode_token, hash_password, verify_password)
from app.models import Role, User


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _issue_tokens(self, user: User) -> dict:
        return {
            "access_token": create_access_token(user.id, user.role),
            "refresh_token": create_refresh_token(user.id, user.role),
            "token_type": "Bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    def login(self, username: str, password: str) -> dict:
        user = self.db.scalar(select(User).where(User.username == username))
        # Sai username và sai mật khẩu phải trả CÙNG một thông báo lỗi — nếu
        # phân biệt, kẻ tấn công dò được username nào tồn tại trong hệ thống.
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Sai tên đăng nhập hoặc mật khẩu",
                                    code="INVALID_CREDENTIALS")
        if not user.is_active:
            raise UnauthorizedError("Tài khoản đã bị khóa", code="USER_INACTIVE")
        return self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = self.db.get(User, int(payload["sub"]))
        if not user or not user.is_active:
            raise UnauthorizedError("Tài khoản không tồn tại hoặc đã bị khóa",
                                    code="USER_INACTIVE")
        return self._issue_tokens(user)

    def create_user(self, username: str, full_name: str, password: str,
                    role: Role) -> User:
        if self.db.scalar(select(User.id).where(User.username == username)):
            raise UnauthorizedError("Tên đăng nhập đã tồn tại",
                                    code="DUPLICATE_USERNAME")
        user = User(username=username, full_name=full_name,
                   password_hash=hash_password(password), role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: int, full_name: str, role: Role) -> User:
        user = self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User", user_id)
        user.full_name = full_name
        user.role = role
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_active(self, user_id: int, is_active: bool) -> User:
        user = self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User", user_id)
        user.is_active = is_active
        self.db.commit()
        self.db.refresh(user)
        return user
