"""TODO — endpoint housekeeping.

Các endpoint cần viết:
    GET   /tasks?date=&status=&assignee_id=
    POST  /tasks                 201
    PATCH /tasks/{task_id}       phân công hoặc đánh dấu hoàn thành
    GET   /room-status           bảng trạng thái toàn bộ phòng

Xem room_types.py làm mẫu. Nhớ: bọc response bằng ok(), khai báo quyền bằng
Depends(require_*), và có summary= để Swagger đọc được.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/housekeeping", tags=["10. Buồng phòng"])
