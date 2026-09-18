"""Tra cứu phòng trống — nghiệp vụ khó nhất. Xem R3.

Test tương ứng: tests/test_availability.py
"""
import datetime as dt

from sqlalchemy.orm import Session

from app.models.room import Room  # noqa: F401
from app.services.pricing_service import PricingService


class AvailabilityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pricing = PricingService(db)

    # ------------------------------------------------------------- helper
    def _total_rooms_by_type(self, guests: int | None = None) -> dict[int, int]:
        """Số phòng bán được của từng loại → {room_type_id: count}.

        TODO:
          - JOIN Room với RoomType
          - WHERE Room.status != OutOfOrder      ← loại phòng bảo trì
          - nếu có guests: WHERE RoomType.capacity >= guests
          - GROUP BY room_type_id
        """
        raise NotImplementedError("TODO")

    def _occupied_count_by_type(
        self, check_in: dt.date, check_out: dt.date,
        exclude_booking_id: int | None = None,
    ) -> dict[int, int]:
        """Số phòng đang bị chiếm trong khoảng ngày → {room_type_id: count}.

        TODO — JOIN BookingDetail với Booking, WHERE:
          - Booking.status IN BLOCKING_STATUSES   (chỉ Confirmed + CheckedIn)
          - Booking.deleted_at IS NULL
          - Booking.check_in  <  check_out        ┐ công thức giao nhau
          - Booking.check_out >  check_in         ┘ hai khoảng thời gian
          - nếu có exclude_booking_id: Booking.id != exclude_booking_id

        ⚠ Dùng < và >, KHÔNG dùng <= và >=.
          Khách A trả phòng ngày 05, khách B nhận phòng ngày 05 → không trùng.
          Đây là case biên hay sai nhất, có test riêng cho nó.

        ⚠ exclude_booking_id dùng khi SỬA booking: không được tính chính nó
          là đang chiếm phòng, nếu không sẽ tự chặn chính mình.
        """
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------- public
    def search(self, check_in: dt.date, check_out: dt.date, guests: int = 1,
               exclude_booking_id: int | None = None):
        """Tra phòng trống theo LOẠI phòng, kèm giá từng đêm và tổng tiền.

        TODO:
          1. Validate check_out > check_in, không thì raise BusinessError.
          2. totals   = _total_rooms_by_type(guests)
          3. occupied = _occupied_count_by_type(check_in, check_out, exclude...)
          4. Với mỗi loại: free = totals[id] - occupied.get(id, 0)
             Bỏ qua nếu free <= 0.
          5. Gọi pricing.get_nightly_rates để lấy giá từng đêm + tổng tiền.
          6. Trả về AvailabilitySearchOut.

        ⚠ Trả về theo LOẠI phòng ("còn 3 phòng Deluxe"), không phải phòng
          cụ thể. Phòng vật lý chỉ gán lúc check-in.
        """
        raise NotImplementedError("TODO")

    def count_available(self, room_type_id: int, check_in: dt.date,
                        check_out: dt.date,
                        exclude_booking_id: int | None = None) -> int:
        """Số phòng còn trống của MỘT loại. Dùng khi tạo/sửa booking.

        TODO: total - occupied cho đúng room_type_id đó.
        """
        raise NotImplementedError("TODO")

    def free_rooms(self, room_type_id: int, check_in: dt.date,
                   check_out: dt.date) -> list[Room]:
        """Danh sách PHÒNG CỤ THỂ còn trống — dùng lúc check-in để gán phòng.

        TODO:
          - Subquery lấy room_id đã bị chiếm (cùng điều kiện giao nhau như trên,
            thêm BookingDetail.room_id IS NOT NULL)
          - SELECT Room WHERE room_type_id khớp
                       AND status != OutOfOrder
                       AND id NOT IN (subquery)
          - ORDER BY floor, room_number
        """
        raise NotImplementedError("TODO")
