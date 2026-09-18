"""Hash mật khẩu và phát hành / xác thực JWT."""
import datetime as dt
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def _create_token(subject: str, role: str, expires: dt.timedelta,
                  token_type: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    return _create_token(
        str(user_id), role,
        dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(user_id: int, role: str) -> str:
    return _create_token(
        str(user_id), role,
        dt.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def decode_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET,
                             algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token đã hết hạn", code="TOKEN_EXPIRED")
    except jwt.PyJWTError:
        raise UnauthorizedError("Token không hợp lệ", code="TOKEN_INVALID")

    if payload.get("type") != expected_type:
        raise UnauthorizedError("Sai loại token", code="TOKEN_WRONG_TYPE")
    return payload
