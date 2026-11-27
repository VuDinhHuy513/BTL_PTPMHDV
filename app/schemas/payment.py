"""DTO cho folio, thanh toán, hóa đơn. Xem R9.

Hệ thống KHÔNG xử lý tiền thật: thu tiền mặt / chuyển khoản làm bên ngoài, lễ tân
chỉ GHI SỔ lại ở đây để folio biết khách đã trả bao nhiêu.
"""
import datetime as dt
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import BookingStatus, PaymentMethod
from app.schemas.common import ORMBase


class PaymentIn(BaseModel):
    # max_digits/decimal_places khớp kiểu cột Numeric(18, 2): không cho số lẻ 3 chữ số
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    method: PaymentMethod = PaymentMethod.CASH
    note: str | None = Field(default=None, max_length=255)


class RefundIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    reason: str = Field(min_length=1, max_length=200)


class PaymentOut(ORMBase):
    id: int
    booking_id: int
    amount: Decimal                 # dương = thu, âm = hoàn
    method: PaymentMethod
    note: str | None = None
    paid_at: dt.datetime


class FolioLine(BaseModel):
    """Một dòng trên bảng kê: một đêm của một phòng, hoặc một lần dùng dịch vụ."""
    type: Literal["room", "service"]
    date: dt.date
    description: str
    quantity: int
    unit_price: Decimal
    amount: Decimal


class FolioOut(BaseModel):
    booking_id: int
    booking_code: str
    status: BookingStatus
    customer_name: str
    customer_phone: str
    check_in: dt.date
    check_out: dt.date
    nights: int
    lines: list[FolioLine]
    room_charge: Decimal
    service_charge: Decimal
    subtotal: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    total: Decimal
    paid: Decimal                   # tổng payments (thu trừ hoàn)
    balance_due: Decimal            # total − paid; âm nghĩa là đang thu dư


class InvoiceOut(FolioOut):
    """Hóa đơn để in: số tiền lấy từ bản ghi invoices (đã chốt lúc check-out),
    còn paid/balance_due tính lại lúc xem vì khách có thể trả sau."""
    id: int
    code: str
    issued_at: dt.datetime


class InvoiceSummaryOut(BaseModel):
    """Một dòng trong danh sách hóa đơn — gọn, không kèm bảng kê."""
    id: int
    code: str
    issued_at: dt.datetime
    booking_id: int
    booking_code: str
    customer_name: str
    total: Decimal
