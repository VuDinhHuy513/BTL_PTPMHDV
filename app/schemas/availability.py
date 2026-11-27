import datetime as dt
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import BookingStatus, RoomStatus


class NightRateOut(BaseModel):
    date: dt.date
    price: Decimal


class RoomBriefOut(BaseModel):
    id: int
    room_number: str
    floor: int


class AvailabilityOut(BaseModel):
    room_type_id: int
    name: str
    capacity: int
    available_count: int
    rooms: list[RoomBriefOut]           # các phòng cụ thể còn trống, để lễ tân chọn
    nightly_rates: list[NightRateOut]   # giá từng đêm của MỘT phòng loại này
    total_price: Decimal                # tổng tiền của MỘT phòng loại này


class AvailabilitySearchOut(BaseModel):
    check_in: dt.date
    check_out: dt.date
    nights: int
    guests: int
    room_types: list[AvailabilityOut]


class ScheduleBookingOut(BaseModel):
    """Một booking đang giữ phòng, hiển thị trên sơ đồ phòng."""
    booking_id: int
    code: str
    customer_name: str
    check_in: dt.date
    check_out: dt.date
    status: BookingStatus


class RoomScheduleOut(BaseModel):
    """Một hàng của sơ đồ phòng: phòng + các booking giữ nó trong khoảng xem."""
    room_id: int
    room_number: str
    floor: int
    room_type_id: int
    room_type_name: str
    status: RoomStatus                  # trạng thái HIỆN TẠI (có cả OutOfOrder)
    bookings: list[ScheduleBookingOut]  # rỗng = trống suốt khoảng xem
