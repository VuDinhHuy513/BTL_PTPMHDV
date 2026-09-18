"""TODO — endpoint services.

Các endpoint cần viết:
    GET  /                  danh mục dịch vụ
    POST /                  201, quyền Admin
    PUT  /{service_id}      quyền Admin

Xem room_types.py làm mẫu. Nhớ: bọc response bằng ok(), khai báo quyền bằng
Depends(require_*), và có summary= để Swagger đọc được.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/services", tags=["08. Dịch vụ"])
