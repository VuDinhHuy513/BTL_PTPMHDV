"""Exception nghiệp vụ + handler tập trung.

Service chỉ cần raise, không cần trả về Result<T>. Handler ở main.py
biến mọi exception thành cùng một format JSON.
"""
from typing import Any


class AppException(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, code: str | None = None,
                 details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details


class NotFoundError(AppException):
    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, resource: str, key: Any) -> None:
        super().__init__(f"{resource} với id {key} không tồn tại")


class BusinessError(AppException):
    """Vi phạm quy tắc nghiệp vụ: hết phòng, sai vòng đời trạng thái..."""
    status_code = 409
    code = "BUSINESS_RULE_VIOLATED"


class ForbiddenError(AppException):
    status_code = 403
    code = "FORBIDDEN"


class UnauthorizedError(AppException):
    status_code = 401
    code = "UNAUTHORIZED"
