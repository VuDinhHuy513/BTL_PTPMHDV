"""Booking, BookingDetail, BookingNightRate. Xem R1, R4, R5.

Nhân viên chọn ĐÚNG phòng lúc khách gọi đặt, nên mỗi BookingDetail luôn có room_id.
"""
import datetime as dt
from decimal import Decimal

from sqlalchemy import (Date, DateTime, ForeignKey, Index, Integer, Numeric,
                        String, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import BookingStatus


class Booking(Base):
    """Một lần đặt phòng. Một booking có thể giữ nhiều phòng (booking_details)."""
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    check_in: Mapped[dt.date] = mapped_column(Date)
    check_out: Mapped[dt.date] = mapped_column(Date)
    guests: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[BookingStatus] = mapped_column(
        String(20), default=BookingStatus.CONFIRMED)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now)
    checked_in_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    checked_out_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    # Xóa mềm: KHÔNG xóa cứng bản ghi, mất dữ liệu báo cáo (R10)
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="bookings")
    details: Mapped[list["BookingDetail"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan",
        order_by="BookingDetail.id")
    services: Mapped[list["BookingService"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="booking")
    invoice: Mapped["Invoice | None"] = relationship(
        back_populates="booking", uselist=False)

    # Query nóng nhất hệ thống (tra phòng trống); không có index sẽ chậm.
    __table_args__ = (
        Index("ix_bookings_check_in_out_status", "check_in", "check_out", "status"),
    )

    @property
    def nights(self) -> int:
        # check_out không tính đêm: 01→05 là 4 đêm (R1)
        return (self.check_out - self.check_in).days


class BookingDetail(Base):
    """Mỗi dòng là MỘT phòng trong booking."""
    __tablename__ = "booking_details"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    # Bắt buộc có: loại phòng suy ra từ room.room_type_id, không lưu thừa ở đây
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)

    booking: Mapped[Booking] = relationship(back_populates="details")
    room: Mapped["Room"] = relationship()
    night_rates: Mapped[list["BookingNightRate"]] = relationship(
        back_populates="detail", cascade="all, delete-orphan",
        order_by="BookingNightRate.date")

    @property
    def room_number(self) -> str:
        return self.room.room_number

    @property
    def room_type_id(self) -> int:
        return self.room.room_type_id

    @property
    def room_charge(self) -> Decimal:
        return sum((n.price for n in self.night_rates), Decimal("0"))


class BookingNightRate(Base):
    """Giá CHỐT của từng đêm.

    Cần dù mọi đêm cùng giá: Admin sửa base_price sau này thì booking cũ không
    đổi giá (CONVENTIONS mục 4), và cho phép đổi phòng giữa kỳ sang loại khác giá.
    """
    __tablename__ = "booking_night_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_detail_id: Mapped[int] = mapped_column(
        ForeignKey("booking_details.id"), index=True)
    date: Mapped[dt.date] = mapped_column(Date)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    detail: Mapped[BookingDetail] = relationship(back_populates="night_rates")

    __table_args__ = (
        UniqueConstraint("booking_detail_id", "date", name="uq_night_rate_detail_date"),
    )
