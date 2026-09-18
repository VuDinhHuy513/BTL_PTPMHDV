"""TODO — endpoint users.

Các endpoint cần viết:
    GET   /                      toàn bộ quyền Admin
    POST  /                      201
    PUT   /{user_id}
    PATCH /{user_id}/status      khóa / mở tài khoản

Xem room_types.py làm mẫu. Nhớ: bọc response bằng ok(), khai báo quyền bằng
Depends(require_*), và có summary= để Swagger đọc được.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["12. Quản trị người dùng"])
