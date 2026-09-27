"""Service (danh mục dịch vụ) và BookingService (một lần khách dùng dịch vụ). Xem R9."""
import datetime as dt
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Service(Base):
    """Danh mục dịch vụ: ăn sáng, giặt ủi… Đây là giá HIỆN HÀNH, chưa chốt."""
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    unit: Mapped[str] = mapped_column(String(20))              # "lần" / "kg" / "suất"
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class BookingService(Base):
    """Một dòng dịch vụ khách đã dùng trong booking."""
    __tablename__ = "booking_services"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    used_date: Mapped[dt.date] = mapped_column(Date, default=dt.date.today)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # CHỐT giá lúc dùng, không join sang services khi in bill (CONVENTIONS mục 4)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    booking: Mapped["Booking"] = relationship(back_populates="services")
    service: Mapped[Service] = relationship()

    @property
    def amount(self) -> Decimal:
        return self.unit_price * self.quantity
