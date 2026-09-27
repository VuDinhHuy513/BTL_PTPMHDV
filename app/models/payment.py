"""Payment (thu/hoàn tiền) và Invoice (hóa đơn). Xem R9."""
import datetime as dt
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PaymentMethod


class Payment(Base):
    """Một lần thu hoặc hoàn tiền. Không sửa bản ghi cũ: hoàn tiền là bản ghi mới."""
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    # Số DƯƠNG là thu tiền, số ÂM là hoàn tiền
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    method: Mapped[PaymentMethod] = mapped_column(String(20), default=PaymentMethod.CASH)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now)

    booking: Mapped["Booking"] = relationship(back_populates="payments")


class Invoice(Base):
    """Hóa đơn xuất lúc check-out. Mỗi booking một hóa đơn."""
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id"), unique=True, index=True)
    room_charge: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    service_charge: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    # Lưu cả thuế suất: năm sau đổi thuế thì hóa đơn cũ vẫn giữ con số đã xuất
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    issued_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now)

    booking: Mapped["Booking"] = relationship(back_populates="invoice")
