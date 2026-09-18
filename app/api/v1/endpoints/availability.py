"""TODO — endpoint tra cứu phòng trống.

    GET /availability?check_in=&check_out=&guests=
        → AvailabilityService(db).search(...)
        Quyền: require_any

    GET /availability/rooms?room_type_id=&check_in=&check_out=
        → AvailabilityService(db).free_rooms(...)
        Quyền: require_front_desk

Dùng Query(..., description="...") để Swagger hiển thị gợi ý cho người dùng.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/availability", tags=["05. Tra cứu phòng trống"])
