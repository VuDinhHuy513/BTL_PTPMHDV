"""Dependency dùng chung: DB session, user đang đăng nhập, kiểm tra vai trò.

=========================================================================
FILE MẪU — đã viết sẵn đầy đủ. Dùng require_* trong endpoint như sau:

    @router.post("/bookings")
    def create(dto: BookingCreateIn,
               db: Session = Depends(get_db),
               user: User = Depends(require_front_desk)):
        ...
=========================================================================
"""
from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import Role

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    # TODO: bỏ comment khi đã viết xong model User
    # from app.models.user import User
    if cred is None:
        raise UnauthorizedError("Thiếu access token", code="MISSING_TOKEN")
    payload = decode_token(cred.credentials, expected_type="access")

    raise NotImplementedError(
        "TODO: viết model User rồi nạp user từ DB theo payload['sub'], "
        "kiểm tra is_active, trả về user")


def require_roles(*roles: Role) -> Callable:
    """Trả về dependency chỉ cho phép các vai trò được liệt kê."""
    allowed = {r.value for r in roles}

    def checker(user=Depends(get_current_user)):
        if user.role not in allowed:
            raise ForbiddenError(
                f"Vai trò '{user.role}' không có quyền thực hiện thao tác này")
        return user

    return checker


# Các tổ hợp quyền hay dùng — xem docs/BUSINESS_RULES.md mục R11
# Hệ thống chỉ có 2 vai trò nên "nhân viên" (lễ tân + admin) dùng chung một tổ hợp.
require_admin = require_roles(Role.ADMIN)
require_front_desk = require_roles(Role.ADMIN, Role.RECEPTIONIST)
require_any = get_current_user
