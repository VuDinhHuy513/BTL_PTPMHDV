"""DTO cho booking.

Nhận vào:  BookingCreateIn, WalkInIn, BookingUpdateIn, CancelIn, CheckInIn,
           ChangeRoomIn
Trả về:    BookingOut (+ BookingDetailOut, BookingNightRateOut)

Không có trường `source` trong DTO nhận vào: endpoint quyết định nguồn đặt
(staff/online), người gọi không được tự khai (R13).
"""
import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import BookingSource, BookingStatus
from app.schemas.common import ORMBase
from app.schemas.customer import CustomerIn, CustomerOut
from app.services.booking_service import MAX_NIGHTS_PER_BOOKING


def _validate_new_booking(dto) -> None:
    """Quy tắc chung của mọi booking MỚI (đặt trước lẫn walk-in), viết một chỗ."""
    if dto.customer_id is None and dto.customer is None:
        raise ValueError("Cần customer_id hoặc thông tin customer")
    if dto.check_out <= dto.check_in:
        raise ValueError("check_out phải sau check_in")
    if dto.check_in < dt.date.today():
        raise ValueError("Không được đặt ngày trong quá khứ")
    if (dto.check_out - dto.check_in).days > MAX_NIGHTS_PER_BOOKING:
        raise ValueError(f"Một booking tối đa {MAX_NIGHTS_PER_BOOKING} đêm")
    if len(set(dto.room_ids)) != len(dto.room_ids):
        raise ValueError("Không được chọn trùng một phòng hai lần")


class BookingCreateIn(BaseModel):
    customer_id: int | None = None
    customer: CustomerIn | None = None
    check_in: dt.date
    check_out: dt.date
    guests: int = Field(default=1, ge=1)
    room_ids: list[int] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate(self):
        _validate_new_booking(self)
        return self


class WalkInIn(BaseModel):
    """Khách vãng lai: giống đặt phòng nhưng KHÔNG gửi check_in — luôn là hôm nay."""
    customer_id: int | None = None
    customer: CustomerIn | None = None
    check_out: dt.date
    guests: int = Field(default=1, ge=1)
    room_ids: list[int] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=500)
    id_card_number: str | None = Field(default=None, max_length=20)

    @property
    def check_in(self) -> dt.date:
        # Property chứ không phải field: client không gửi được, nhưng
        # BookingService.create() vẫn đọc được dto.check_in như booking thường
        return dt.date.today()

    @model_validator(mode="after")
    def _validate(self):
        _validate_new_booking(self)
        return self


class CheckInIn(BaseModel):
    # Không bắt buộc: khách quen đã có số giấy tờ trong hồ sơ từ lần trước
    id_card_number: str | None = Field(default=None, max_length=20)


class ChangeRoomIn(BaseModel):
    booking_detail_id: int
    new_room_id: int
    reason: str | None = Field(default=None, max_length=200)


class BookingUpdateIn(BaseModel):
    """PUT = gửi lại ĐỦ các trường sửa được (thay thế toàn bộ), không gửi phần lẻ.

    Không có room_ids: đổi phòng dùng POST /bookings/{id}/change-room (R6).
    Không kiểm tra "ngày quá khứ" ở đây: chỉ chặn khi check_in BỊ ĐỔI, mà muốn
    biết có đổi hay không phải so với DB → việc của service.
    """
    check_in: dt.date
    check_out: dt.date
    guests: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out phải sau check_in")
        if (self.check_out - self.check_in).days > MAX_NIGHTS_PER_BOOKING:
            raise ValueError(f"Một booking tối đa {MAX_NIGHTS_PER_BOOKING} đêm")
        return self


class CancelIn(BaseModel):
    # Bắt buộc ghi lý do (R10). strip để chuỗi toàn dấu cách "   " cũng bị chặn.
    # 255 = độ dài cột bookings.cancel_reason
    reason: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def _strip(self):
        self.reason = self.reason.strip()
        if not self.reason:
            raise ValueError("Lý do hủy không được để trống")
        return self


class BookingNightRateOut(ORMBase):
    date: dt.date
    price: Decimal


class BookingDetailOut(ORMBase):
    id: int
    room_id: int
    room_number: str
    room_type_id: int
    night_rates: list[BookingNightRateOut]


class BookingOut(ORMBase):
    id: int
    code: str
    customer: CustomerOut
    check_in: dt.date
    check_out: dt.date
    nights: int
    guests: int
    status: BookingStatus
    source: BookingSource
    note: str | None = None
    cancel_reason: str | None = None
    created_at: dt.datetime
    checked_in_at: dt.datetime | None = None
    checked_out_at: dt.datetime | None = None
    details: list[BookingDetailOut]
    room_charge: Decimal
