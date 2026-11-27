"""DTO cho dịch vụ: danh mục (Service) và dòng dịch vụ trong booking (BookingService)."""
import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase

# Một lần ghi nhận tối đa bao nhiêu đơn vị — chặn gõ nhầm 1000 suất ăn sáng
MAX_SERVICE_QUANTITY = 100


class ServiceIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=20)         # "suất", "lần", "kg"
    # 18 chữ số, 2 số lẻ = đúng kiểu Numeric(18, 2) của cột; cho phép 0 (dịch vụ miễn phí)
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)


class ServiceOut(ORMBase):
    id: int
    name: str
    unit: str
    unit_price: Decimal


class BookingServiceIn(BaseModel):
    service_id: int
    quantity: int = Field(default=1, ge=1, le=MAX_SERVICE_QUANTITY)
    used_date: dt.date | None = None          # bỏ trống = hôm nay
    note: str | None = Field(default=None, max_length=255)


class BookingServiceOut(ORMBase):
    id: int
    service_id: int
    service_name: str
    unit: str
    quantity: int
    unit_price: Decimal                       # giá ĐÃ CHỐT lúc ghi nhận
    amount: Decimal
    used_date: dt.date
    note: str | None = None
