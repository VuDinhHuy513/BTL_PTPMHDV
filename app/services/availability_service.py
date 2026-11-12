"""Tra cứu phòng trống — nghiệp vụ khó nhất. Xem R3.

Nhân viên chọn ĐÚNG phòng lúc đặt, nên "trống" được xét cho từng phòng cụ thể:
một phòng bận nếu có booking Confirmed/CheckedIn giữ chính phòng đó và giao
nhau về ngày. Số phòng trống của một loại = số phòng của loại đó không bận.

Test tương ứng: tests/test_availability.py
"""
import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.models import BLOCKING_STATUSES, Booking, BookingDetail, Room, RoomStatus, RoomType
from app.schemas.availability import (AvailabilityOut, AvailabilitySearchOut,
                                      NightRateOut, RoomBriefOut)
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
        """Id các phòng đang bị chiếm trong khoảng ngày [check_in, check_out).

        Dùng < và >, KHÔNG dùng <= và >=: khách A trả phòng ngày 05, khách B
        nhận phòng ngày 05 → không trùng. exclude_booking_id dùng khi SỬA booking
        để không tự chặn chính nó.
        """
        stmt = (select(BookingDetail.room_id)
                .join(Booking, Booking.id == BookingDetail.booking_id)
                .where(Booking.status.in_([s.value for s in BLOCKING_STATUSES]),
                       Booking.deleted_at.is_(None),
                       Booking.check_in < check_out,
                       Booking.check_out > check_in))
        if exclude_booking_id is not None:
            stmt = stmt.where(Booking.id != exclude_booking_id)
        return set(self.db.scalars(stmt).all())

    # ------------------------------------------------------------- public
    def free_rooms(self, room_type_id: int, check_in: dt.date,
                   check_out: dt.date,
                   exclude_booking_id: int | None = None) -> list[Room]:
        """Danh sách PHÒNG CỤ THỂ còn trống của một loại — lễ tân chọn từ đây.

        Không lọc theo Dirty/Occupied: đó là trạng thái HIỆN TẠI, phòng đang
        Dirty hôm nay vẫn bán được cho ngày mai. Việc phòng đã sẵn sàng hay
        chưa chỉ kiểm tra lúc check-in.
        """
        busy = self._busy_room_ids(check_in, check_out, exclude_booking_id)
        stmt = (select(Room)
                .where(Room.room_type_id == room_type_id,
                       Room.status != RoomStatus.OUT_OF_ORDER.value)
                .order_by(Room.floor, Room.room_number))
        if busy:
            stmt = stmt.where(Room.id.not_in(busy))
        return list(self.db.scalars(stmt).all())

    def count_available(self, room_type_id: int, check_in: dt.date,
                        check_out: dt.date,
                        exclude_booking_id: int | None = None) -> int:
        """Số phòng còn trống của MỘT loại."""
        return len(self.free_rooms(room_type_id, check_in, check_out,
                                   exclude_booking_id))

    def search(self, check_in: dt.date, check_out: dt.date, guests: int = 1,
               exclude_booking_id: int | None = None):
        """Tra phòng trống theo LOẠI, kèm danh sách phòng cụ thể, giá và tổng tiền.

        guests chỉ là bộ lọc "một phòng chứa đủ cả nhóm"; nhóm đông có thể đặt
        nhiều phòng, việc kiểm tra tổng sức chứa nằm ở BookingService.create.
        """
        if check_out <= check_in:
            raise BusinessError("Ngày trả phòng phải sau ngày nhận phòng",
                                code="INVALID_DATE_RANGE")

        room_types = self.db.scalars(
            select(RoomType).where(RoomType.capacity >= guests)
            .order_by(RoomType.base_price)).all()

        result: list[AvailabilityOut] = []
        for rt in room_types:
            rooms = self.free_rooms(rt.id, check_in, check_out, exclude_booking_id)
            if not rooms:
                continue
            rates = self.pricing.get_nightly_rates(rt.id, check_in, check_out)
            result.append(AvailabilityOut(
                room_type_id=rt.id, name=rt.name, capacity=rt.capacity,
                available_count=len(rooms),
                rooms=[RoomBriefOut(id=r.id, room_number=r.room_number,
                                    floor=r.floor) for r in rooms],
                nightly_rates=[NightRateOut(date=d, price=p) for d, p in rates],
                total_price=sum((p for _, p in rates), Decimal("0"))))

        return AvailabilitySearchOut(
            check_in=check_in, check_out=check_out,
            nights=(check_out - check_in).days, guests=guests,
            room_types=result)

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
