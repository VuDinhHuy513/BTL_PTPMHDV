"""User: tài khoản nhân viên (Admin hoặc Lễ tân)."""
import datetime as dt

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    # LƯU HASH, không bao giờ lưu mật khẩu thô. Dùng hash_password ở app/core/security.py
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(String(20), default=Role.RECEPTIONIST)
    # Khóa tài khoản (nghỉ việc, tạm khóa) mà không xóa dữ liệu
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now)
