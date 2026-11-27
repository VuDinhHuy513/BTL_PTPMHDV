"""Tra cứu phòng trống — nghiệp vụ khó nhất. Xem R3.

Nhân viên chọn ĐÚNG phòng lúc đặt, nên "trống" được xét cho từng phòng cụ thể:
một phòng bận nếu có booking Confirmed/CheckedIn giữ chính phòng đó và giao
nhau về ngày. Số phòng trống của một loại = số phòng của loại đó không bận.

Test tương ứng: tests/test_availability.py
"""
import datetime as dt
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.models import (BLOCKING_STATUSES, Booking, BookingDetail, Customer, Room,
                        RoomStatus, RoomType)
from app.schemas.availability import (AvailabilityOut, AvailabilitySearchOut,
                                      NightRateOut, RoomBriefOut, RoomScheduleOut,
                                      ScheduleBookingOut)
from app.services.pricing_service import PricingService

# Sơ đồ phòng xem tối đa ~2 tháng một lần: đủ cho lễ tân, không quét cả năm
MAX_SCHEDULE_DAYS = 62


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

    def schedule(self, from_date: dt.date, to_date: dt.date) -> list[RoomScheduleOut]:
        """Sơ đồ phòng theo ngày: mỗi phòng kèm các booking đang giữ nó trong
        khoảng [from_date, to_date). Phục vụ GET /rooms/schedule.

        Đúng 2 truy vấn dù khách sạn có bao nhiêu phòng: một lấy mọi phòng, một
        lấy MỌI booking giao khoảng rồi chia theo room_id bằng Python. Truy vấn
        từng phòng một là lỗi N+1 (48 phòng = 49 truy vấn).
        """
        if to_date <= from_date:
            raise BusinessError("Ngày kết thúc phải sau ngày bắt đầu",
                                code="INVALID_DATE_RANGE")
        if (to_date - from_date).days > MAX_SCHEDULE_DAYS:
            raise BusinessError(
                f"Sơ đồ phòng xem tối đa {MAX_SCHEDULE_DAYS} ngày mỗi lần",
                code="DATE_RANGE_TOO_LONG")

        # Lấy MỌI phòng, kể cả OutOfOrder: sơ đồ phải cho thấy phòng đang bảo trì
        rooms = self.db.execute(
            select(Room, RoomType.name)
            .join(RoomType, RoomType.id == Room.room_type_id)
            .order_by(Room.floor, Room.room_number)).all()

        # Chỉ booking đang GIỮ phòng (Confirmed/CheckedIn), cùng công thức giao
        # nhau < và > với tra phòng trống (R3)
        rows = self.db.execute(
            select(BookingDetail.room_id, Booking.id, Booking.code,
                   Customer.full_name, Booking.check_in, Booking.check_out,
                   Booking.status)
            .join(Booking, Booking.id == BookingDetail.booking_id)
            .join(Customer, Customer.id == Booking.customer_id)
            .where(Booking.status.in_([s.value for s in BLOCKING_STATUSES]),
                   Booking.deleted_at.is_(None),
                   Booking.check_in < to_date,
                   Booking.check_out > from_date)
            .order_by(Booking.check_in)).all()

        by_room: dict[int, list[ScheduleBookingOut]] = defaultdict(list)
        for room_id, booking_id, code, name, check_in, check_out, status in rows:
            by_room[room_id].append(ScheduleBookingOut(
                booking_id=booking_id, code=code, customer_name=name,
                check_in=check_in, check_out=check_out, status=status))

        return [RoomScheduleOut(
                    room_id=room.id, room_number=room.room_number, floor=room.floor,
                    room_type_id=room.room_type_id, room_type_name=type_name,
                    status=room.status, bookings=by_room.get(room.id, []))
                for room, type_name in rooms]
