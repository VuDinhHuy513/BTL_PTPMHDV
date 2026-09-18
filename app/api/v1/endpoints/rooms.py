"""TODO — endpoint rooms.

Các endpoint cần viết:
    GET    /                       lọc theo floor / room_type_id / status
    GET    /{room_id}
    POST   /                       201, quyền Admin
    PUT    /{room_id}              quyền Admin
    PATCH  /{room_id}/status       quyền Admin + Housekeeper
    DELETE /{room_id}              chặn nếu phòng đã gắn booking

Xem room_types.py làm mẫu. Nhớ: bọc response bằng ok(), khai báo quyền bằng
Depends(require_*), và có summary= để Swagger đọc được.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/rooms", tags=["03. Phòng"])
