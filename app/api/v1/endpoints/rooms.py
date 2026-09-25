"""TODO — endpoint rooms.

Các endpoint cần viết:
    GET    /                       lọc theo floor / room_type_id / status
    GET    /schedule?from=&to=     sơ đồ phòng theo ngày (xem bên dưới)
    GET    /{room_id}
    POST   /                       201, quyền Admin
    PUT    /{room_id}              quyền Admin
    PATCH  /{room_id}/status       quyền Admin + Lễ tân (dọn xong → Available,
                                   đưa đi/về bảo trì → OutOfOrder)
    DELETE /{room_id}              chặn nếu phòng đã gắn booking

GET /schedule → AvailabilityService(db).schedule(from, to), quyền require_front_desk.
    Trả list, mỗi phần tử một phòng:
        {room_id, room_number, floor, room_type, status,
         bookings: [{booking_id, code, customer_name, check_in, check_out, status}]}
    Đây là màn hình lễ tân xem khi khách gọi điện: phòng nào đã có người đặt,
    đặt từ ngày nào đến ngày nào. Cần thêm DTO RoomScheduleOut vào schemas/room.py.

⚠ Khai báo /schedule TRƯỚC /{room_id}, nếu không "schedule" bị khớp vào {room_id}.

Xem room_types.py làm mẫu. Nhớ: bọc response bằng ok(), khai báo quyền bằng
Depends(require_*), và có summary= để Swagger đọc được.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/rooms", tags=["03. Phòng"])
