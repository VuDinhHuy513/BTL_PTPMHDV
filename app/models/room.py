"""=========================================================================
   FILE MẪU — đọc kỹ file này trước, các model khác viết theo đúng kiểu này.
   ========================================================================="""
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RoomStatus


class RoomType(Base):
    """Loại phòng: Standard, Deluxe, Suite…"""
    __tablename__ = "room_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    capacity: Mapped[int] = mapped_column(Integer)
    # Numeric chứ không phải Float: tiền bạc dùng float sẽ sai số
    base_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    rooms: Mapped[list["Room"]] = relationship(back_populates="room_type")


class Room(Base):
    """Phòng vật lý: 101, 102, 201…"""
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    floor: Mapped[int] = mapped_column(Integer)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id"), index=True)
    # Enum, không phải chuỗi tự do — xem docs/CONVENTIONS.md mục 3
    status: Mapped[RoomStatus] = mapped_column(String(20), default=RoomStatus.AVAILABLE)

    room_type: Mapped[RoomType] = relationship(back_populates="rooms")
