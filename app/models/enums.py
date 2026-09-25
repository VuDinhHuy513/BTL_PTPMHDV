"""Enum nghiệp vụ."""
from enum import Enum


class Role(str, Enum):
    ADMIN = "Admin"
    RECEPTIONIST = "Receptionist"     # Lễ tân: kiêm luôn phần thu ngân/kế toán


class RoomStatus(str, Enum):
    """Trạng thái HIỆN TẠI của phòng — không phản ánh lịch đặt trong tương lai."""
    AVAILABLE = "Available"           # đã dọn sạch, sẵn sàng nhận khách
    OCCUPIED = "Occupied"             # đang có khách
    DIRTY = "Dirty"                   # khách vừa trả, chờ dọn (dọn xong lễ tân đổi về Available)
    OUT_OF_ORDER = "OutOfOrder"       # đang bảo trì, không bán được


class BookingStatus(str, Enum):
    CONFIRMED = "Confirmed"           # đã đặt trước (nhân viên đặt xong là chốt luôn)
    CHECKED_IN = "CheckedIn"
    CHECKED_OUT = "CheckedOut"
    CANCELLED = "Cancelled"
    NO_SHOW = "NoShow"


# Chỉ 2 trạng thái này mới thực sự chiếm phòng.
# Cancelled/NoShow/CheckedOut KHÔNG chặn phòng.
BLOCKING_STATUSES = (BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN)


class PaymentMethod(str, Enum):
    CASH = "Cash"
    CARD = "Card"
    TRANSFER = "Transfer"
