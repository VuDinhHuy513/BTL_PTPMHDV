"""TODO — endpoint customers.

Các endpoint cần viết:
    GET  /?search=&page=&limit=    tìm theo tên/sđt/email, có PageMeta
    GET  /{customer_id}
    GET  /{customer_id}/bookings   lịch sử đặt phòng
    POST /                         201
    PUT  /{customer_id}

Xem room_types.py làm mẫu. Nhớ: bọc response bằng ok(), khai báo quyền bằng
Depends(require_*), và có summary= để Swagger đọc được.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/customers", tags=["05. Khách hàng"])
