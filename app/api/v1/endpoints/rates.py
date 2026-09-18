"""TODO — endpoint rates.

Các endpoint cần viết:
    GET    /?room_type_id=&from=&to=
    POST   /            201, đặt giá 1 ngày (đã có thì ghi đè)
    POST   /bulk        201, đặt giá cả khoảng, lọc được theo thứ
    DELETE /{rate_id}   xóa override, quay về base_price

Xem room_types.py làm mẫu. Nhớ: bọc response bằng ok(), khai báo quyền bằng
Depends(require_*), và có summary= để Swagger đọc được.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/rates", tags=["04. Giá phòng"])
