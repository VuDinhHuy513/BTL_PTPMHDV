"""TODO — endpoint tra cứu phòng trống.

    GET /availability?check_in=&check_out=&guests=
        → AvailabilityService(db).search(...)
        Trả từng loại phòng kèm danh sách phòng cụ thể còn trống.
        guests không bắt buộc (mặc định 1): chỉ để lọc loại phòng mà một phòng
        chứa đủ cả nhóm.
        Quyền: require_front_desk

    GET /availability/rooms?room_type_id=&check_in=&check_out=
        → AvailabilityService(db).free_rooms(...)
        Danh sách phòng cụ thể còn trống của một loại.
        Quyền: require_front_desk

Dùng Query(..., description="...") để Swagger hiển thị gợi ý cho người dùng.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/availability", tags=["04. Tra cứu phòng trống"])
