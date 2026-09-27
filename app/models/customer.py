"""Customer: khách hàng.

phone dùng để nhận diện khách cũ: khi tạo booking, tìm khách theo số điện thoại,
có rồi thì dùng lại, chưa có mới tạo (R5). id_card_number được ghi lúc check-in.
"""
import datetime as dt

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100), index=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    id_card_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="customer")
