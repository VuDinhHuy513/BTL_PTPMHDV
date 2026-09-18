"""TODO — endpoint auth.

Các endpoint cần viết:
    POST /login       → AuthService.login, trả access + refresh token
    POST /refresh     → cấp lại access token
    POST /logout      → token stateless nên chỉ báo client xóa token
    GET  /me          → thông tin người đang đăng nhập

Xem room_types.py làm mẫu. Nhớ: bọc response bằng ok(), khai báo quyền bằng
Depends(require_*), và có summary= để Swagger đọc được.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["01. Xác thực"])
