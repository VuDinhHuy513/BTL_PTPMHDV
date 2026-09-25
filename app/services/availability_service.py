"""Tra cứu phòng trống — nghiệp vụ khó nhất. Xem R3.

Nhân viên chọn ĐÚNG phòng lúc đặt, nên "trống" được xét cho từng phòng cụ thể:
một phòng bận nếu có booking Confirmed/CheckedIn giữ chính phòng đó và giao
nhau về ngày. Số phòng trống của một loại = số phòng của loại đó không bận.

Test tương ứng: tests/test_availability.py
"""
import datetime as dt

from sqlalchemy.orm import Session

from app.models.room import Room
from app.services.pricing_service import PricingService


class AvailabilityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pricing = PricingService(db)

    # ------------------------------------------------------------- helper
    def _busy_room_ids(
        self, check_in: dt.date, check_out: dt.date,
        exclude_booking_id: int | None = None,
    ) -> set[int]:
        """Id các phòng đang bị chiếm trong khoảng ngày.

        TODO — JOIN BookingDetail với Booking, lấy BookingDetail.room_id, WHERE:
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
    def free_rooms(self, room_type_id: int, check_in: dt.date,
                   check_out: dt.date,
                   exclude_booking_id: int | None = None) -> list[Room]:
        """Danh sách PHÒNG CỤ THỂ còn trống của một loại — lễ tân chọn từ đây.

        TODO:
          - busy = self._busy_room_ids(check_in, check_out, exclude_booking_id)
          - SELECT Room WHERE room_type_id khớp
                       AND status != OutOfOrder
                       AND id NOT IN busy
          - ORDER BY floor, room_number

        Không lọc theo Dirty/Occupied: đó là trạng thái HIỆN TẠI, phòng đang
        Dirty hôm nay vẫn bán được cho ngày mai. Việc phòng đã sẵn sàng hay
        chưa chỉ kiểm tra lúc check-in.
        """
        raise NotImplementedError("TODO")

    def count_available(self, room_type_id: int, check_in: dt.date,
                        check_out: dt.date,
                        exclude_booking_id: int | None = None) -> int:
        """Số phòng còn trống của MỘT loại. TODO: len(free_rooms(...))."""
        raise NotImplementedError("TODO")

    def search(self, check_in: dt.date, check_out: dt.date, guests: int = 1,
               exclude_booking_id: int | None = None):
        """Tra phòng trống theo LOẠI, kèm danh sách phòng cụ thể, giá và tổng tiền.

        TODO:
          1. Validate check_out > check_in, không thì raise BusinessError.
          2. Lấy các loại phòng có capacity >= guests. guests chỉ là bộ lọc
             "một phòng chứa đủ cả nhóm"; không truyền thì guests=1 (hiện tất
             cả loại). Nhóm đông có thể đặt nhiều phòng, việc kiểm tra tổng
             sức chứa nằm ở BookingService.create.
          3. Với mỗi loại: rooms = free_rooms(...). Bỏ qua nếu rỗng.
          4. Gọi pricing.get_nightly_rates để lấy giá từng đêm + tổng tiền
             (của MỘT phòng loại đó).
          5. Trả về AvailabilitySearchOut; available_count = len(rooms).
        """
        raise NotImplementedError("TODO")

    def schedule(self, from_date: dt.date, to_date: dt.date):
        """Sơ đồ phòng theo ngày: mỗi phòng kèm các booking đang giữ nó trong
        khoảng [from_date, to_date). Phục vụ GET /rooms/schedule.

        TODO:
          - Lấy mọi phòng (kể cả OutOfOrder, ghi rõ trạng thái), ORDER BY floor,
            room_number.
          - Với mỗi phòng: các booking BLOCKING_STATUSES, chưa xóa mềm, giao
            nhau với khoảng (cùng công thức < và >) → [{booking_id, code,
            customer_name, check_in, check_out, status}].
          - Gom bằng MỘT truy vấn cho tất cả booking rồi chia theo room_id,
            đừng truy vấn từng phòng một (N+1).
          - Giới hạn khoảng tối đa 62 ngày (đặt tên hằng số) để không quét quá lớn.
        """
        raise NotImplementedError("TODO")
