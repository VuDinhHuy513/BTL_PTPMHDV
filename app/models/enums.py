"""Enum nghiệp vụ."""
from enum import Enum


class Role(str, Enum):
    ADMIN = "Admin"
    RECEPTIONIST = "Receptionist"     # Lễ tân
    HOUSEKEEPER = "Housekeeper"       # Buồng phòng
    ACCOUNTANT = "Accountant"         # Kế toán


class RoomStatus(str, Enum):
    AVAILABLE = "Available"           # sẵn sàng bán
    OCCUPIED = "Occupied"             # đang có khách
    DIRTY = "Dirty"                   # khách vừa trả, chờ dọn
    INSPECTED = "Inspected"           # đã dọn, chờ kiểm tra
    OUT_OF_ORDER = "OutOfOrder"       # đang bảo trì, không bán được


class BookingStatus(str, Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    CHECKED_IN = "CheckedIn"
    CHECKED_OUT = "CheckedOut"
    CANCELLED = "Cancelled"
    NO_SHOW = "NoShow"


# Chỉ 2 trạng thái này mới thực sự chiếm phòng.
# Pending/Cancelled/NoShow/CheckedOut KHÔNG chặn phòng.
BLOCKING_STATUSES = (BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN)


class PaymentMethod(str, Enum):
    CASH = "Cash"
    CARD = "Card"
    TRANSFER = "Transfer"


class HousekeepingStatus(str, Enum):
    PENDING = "Pending"
    IN_PROGRESS = "InProgress"
    DONE = "Done"
