"""DTO cho booking.

Đã viết: BookingCreateIn, BookingOut (+ BookingDetailOut, BookingNightRateOut).

TODO (làm cùng các endpoint tương ứng):
    BookingUpdateIn    check_in, check_out, guests, note
    CancelIn           reason (min_length=1)
    CheckInIn          id_card_number (không bắt buộc)
    WalkInIn           customer, check_out, guests, room_ids[], note
    ChangeRoomIn       booking_detail_id, new_room_id, reason

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
        if self.customer_id is None and self.customer is None:
            raise ValueError("Cần customer_id hoặc thông tin customer")
        if self.check_out <= self.check_in:
            raise ValueError("check_out phải sau check_in")
        if self.check_in < dt.date.today():
            raise ValueError("Không được đặt ngày trong quá khứ")
        if (self.check_out - self.check_in).days > MAX_NIGHTS_PER_BOOKING:
            raise ValueError(f"Một booking tối đa {MAX_NIGHTS_PER_BOOKING} đêm")
        if len(set(self.room_ids)) != len(self.room_ids):
            raise ValueError("Không được chọn trùng một phòng hai lần")
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
