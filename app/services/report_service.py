"""Báo cáo quản trị. Xem R12.

    Occupancy = đêm-phòng đã bán / đêm-phòng có thể bán × 100
    ADR       = doanh thu phòng / đêm-phòng đã bán
    RevPAR    = doanh thu phòng / đêm-phòng có thể bán
    "đêm-phòng có thể bán" = số phòng không bảo trì × số ngày trong kỳ

Mẹo tính: mỗi dòng booking_night_rates CHÍNH LÀ một đêm-phòng đã bán, kèm giá
đã chốt. Gom nhóm bảng này bằng MỘT truy vấn là ra cả số đêm bán lẫn doanh thu
phòng, không phải duyệt từng booking.

Quy ước:
  - Kỳ báo cáo [from, to] tính CẢ ngày to (báo cáo "từ 01 đến 30").
  - Doanh thu chỉ tính booking CheckedIn/CheckedOut (khách đã thật sự ở), chưa
    gồm VAT. Đêm-phòng "đã bán" dùng cùng điều kiện để ADR = doanh thu / đêm
    khớp nhau.
  - Phòng bảo trì lấy theo trạng thái HIỆN TẠI: hệ thống không lưu lịch sử bảo
    trì nên không biết tháng trước phòng nào từng bảo trì (ghi vào báo cáo).
"""
import datetime as dt
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessError
from app.models import (Booking, BookingDetail, BookingNightRate, BookingStatus,
                        Room, RoomStatus, RoomType, Service)
from app.models import BookingService as BookingServiceLine   # trùng tên class service
from app.schemas.report import (AdrRevparOut, ArrivalDepartureRow, DashboardOut,
                                OccupancyOut, OccupancyRow, RevenueGroupBy,
                                RevenueOut, RevenueRow)

# Khách đã thật sự ở → mới tính doanh thu và đêm-phòng đã bán (R12)
REVENUE_STATUSES = (BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT)
# Danh sách khách đến: còn chờ (Confirmed) và đã đến trong ngày (CheckedIn)
ARRIVAL_STATUSES = (BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN)
# Danh sách khách đi: còn đang ở (CheckedIn) và đã trả trong ngày (CheckedOut)
DEPARTURE_STATUSES = (BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT)

MAX_REPORT_DAYS = 366            # tối đa 1 năm/lần, không quét cả bảng
ZERO = Decimal("0.00")           # 2 số lẻ như mọi ô tiền khác
CENT = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _ratio(numerator, denominator, scale: int = 1) -> Decimal:
    """numerator / denominator × scale, làm tròn 2 số lẻ. Mẫu bằng 0 → 0 thay
    vì ZeroDivisionError (kỳ không bán được đêm nào thì ADR = 0)."""
    if not denominator:
        return ZERO
    return _round(Decimal(numerator) * scale / Decimal(denominator))


def _days(from_date: dt.date, to_date: dt.date) -> list[dt.date]:
    return [from_date + dt.timedelta(days=i) for i in range((to_date - from_date).days + 1)]


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------- OCCUPANCY
    def occupancy(self, from_date: dt.date, to_date: dt.date) -> OccupancyOut:
        days = self._validate_range(from_date, to_date)
        sellable = self._sellable_room_count()
        sold_by_day = self._room_nights_by_date(from_date, to_date)

        rows = []
        for day in days:
            sold = sold_by_day.get(day, (0, ZERO))[0]
            rows.append(OccupancyRow(date=day, available_rooms=sellable, sold_rooms=sold,
                                     occupancy_pct=_ratio(sold, sellable, 100)))
        total_sold = sum(r.sold_rooms for r in rows)
        available = sellable * len(days)
        return OccupancyOut(
            from_date=from_date, to_date=to_date, rows=rows,
            available_room_nights=available, sold_room_nights=total_sold,
            # Tỷ lệ cả kỳ = tổng bán / tổng có thể bán, KHÔNG lấy trung bình các %
            occupancy_pct=_ratio(total_sold, available, 100))

    # ------------------------------------------------------- DOANH THU
    def revenue(self, from_date: dt.date, to_date: dt.date,
                group_by: RevenueGroupBy) -> RevenueOut:
        self._validate_range(from_date, to_date)
        builders = {RevenueGroupBy.DAY: self._revenue_by_day,
                    RevenueGroupBy.ROOM_TYPE: self._revenue_by_room_type,
                    RevenueGroupBy.SERVICE: self._revenue_by_service}
        rows = builders[group_by](from_date, to_date)
        room = sum((r.room_revenue for r in rows), ZERO)
        service = sum((r.service_revenue for r in rows), ZERO)
        return RevenueOut(from_date=from_date, to_date=to_date, group_by=group_by,
                          rows=rows, room_revenue=room, service_revenue=service,
                          total=room + service)

    def _revenue_by_day(self, from_date, to_date) -> list[RevenueRow]:
        rooms = self._room_nights_by_date(from_date, to_date)
        services = dict(self.db.execute(
            self._service_revenue_query(from_date, to_date, BookingServiceLine.used_date)
        ).all())
        rows = []
        for day in _days(from_date, to_date):          # đủ mọi ngày, kể cả ngày 0 đồng
            nights, room_rev = rooms.get(day, (0, ZERO))
            svc_rev = _round(services.get(day) or ZERO)
            rows.append(RevenueRow(key=day.isoformat(), label=f"{day:%d/%m/%Y}",
                                   quantity=nights, room_revenue=_round(room_rev),
                                   service_revenue=svc_rev, total=_round(room_rev) + svc_rev))
        return rows

    def _revenue_by_room_type(self, from_date, to_date) -> list[RevenueRow]:
        # Lưu ý: đổi phòng giữa kỳ thì cả booking_detail ghi phòng MỚI, nên các
        # đêm trước khi đổi cũng tính cho loại phòng mới (giá vẫn đúng giá đã chốt)
        stmt = (self._night_rates_query(from_date, to_date)
                .join(Room, Room.id == BookingDetail.room_id)
                .with_only_columns(Room.room_type_id, func.count(BookingNightRate.id),
                                   func.sum(BookingNightRate.price))
                .group_by(Room.room_type_id))
        sold = {type_id: (count, total) for type_id, count, total in self.db.execute(stmt)}
        rows = []
        for room_type in self.db.scalars(select(RoomType).order_by(RoomType.name)):
            count, total = sold.get(room_type.id, (0, ZERO))
            rows.append(RevenueRow(key=str(room_type.id), label=room_type.name,
                                   quantity=count, room_revenue=_round(total or ZERO),
                                   service_revenue=ZERO, total=_round(total or ZERO)))
        return rows

    def _revenue_by_service(self, from_date, to_date) -> list[RevenueRow]:
        stmt = (self._service_revenue_query(from_date, to_date, BookingServiceLine.service_id)
                .add_columns(func.sum(BookingServiceLine.quantity)))
        used = {sid: (amount, qty) for sid, amount, qty in self.db.execute(stmt)}
        rows = []
        for service in self.db.scalars(select(Service).order_by(Service.name)):
            amount, qty = used.get(service.id, (ZERO, 0))
            amount = _round(amount or ZERO)
            rows.append(RevenueRow(key=str(service.id), label=f"{service.name} ({service.unit})",
                                   quantity=qty or 0, room_revenue=ZERO,
                                   service_revenue=amount, total=amount))
        return rows

    # ------------------------------------------------------- ADR / RevPAR
    def adr_revpar(self, from_date: dt.date, to_date: dt.date) -> AdrRevparOut:
        days = self._validate_range(from_date, to_date)
        by_day = self._room_nights_by_date(from_date, to_date)
        sold = sum(count for count, _ in by_day.values())
        revenue = _round(sum((total for _, total in by_day.values()), ZERO))
        available = self._sellable_room_count() * len(days)
        return AdrRevparOut(
            from_date=from_date, to_date=to_date, days=len(days),
            available_room_nights=available, sold_room_nights=sold, room_revenue=revenue,
            occupancy_pct=_ratio(sold, available, 100),
            adr=_ratio(revenue, sold), revpar=_ratio(revenue, available))

    # ------------------------------------------------------- KHÁCH ĐẾN / ĐI
    def arrivals(self, date: dt.date) -> list[ArrivalDepartureRow]:
        return self._bookings_on(Booking.check_in == date, ARRIVAL_STATUSES)

    def departures(self, date: dt.date) -> list[ArrivalDepartureRow]:
        return self._bookings_on(Booking.check_out == date, DEPARTURE_STATUSES)

    def _bookings_on(self, date_condition, statuses) -> list[ArrivalDepartureRow]:
        stmt = (select(Booking)
                .where(date_condition, Booking.deleted_at.is_(None),
                       Booking.status.in_([s.value for s in statuses]))
                .options(selectinload(Booking.customer),
                         selectinload(Booking.details).selectinload(BookingDetail.room))
                .order_by(Booking.status, Booking.code))
        return [ArrivalDepartureRow(
                    booking_id=b.id, code=b.code, customer_name=b.customer.full_name,
                    customer_phone=b.customer.phone,
                    room_numbers=[d.room.room_number for d in b.details],
                    check_in=b.check_in, check_out=b.check_out, guests=b.guests,
                    status=b.status)
                for b in self.db.scalars(stmt)]

    # ------------------------------------------------------- DASHBOARD
    def dashboard(self) -> DashboardOut:
        today = dt.date.today()
        by_status = Counter(dict(self.db.execute(
            select(Room.status, func.count(Room.id)).group_by(Room.status)).all()))
        sellable = sum(by_status.values()) - by_status[RoomStatus.OUT_OF_ORDER.value]

        def count_bookings(*conditions) -> int:
            return self.db.scalar(select(func.count(Booking.id)).where(
                Booking.deleted_at.is_(None), *conditions))

        tonight = self._room_nights_by_date(today, today).get(today, (0, ZERO))
        service_today = self.db.execute(
            self._service_revenue_query(today, today, BookingServiceLine.used_date)).all()
        return DashboardOut(
            date=today,
            total_rooms=sum(by_status.values()),
            available_rooms=by_status[RoomStatus.AVAILABLE.value],
            occupied_rooms=by_status[RoomStatus.OCCUPIED.value],
            dirty_rooms=by_status[RoomStatus.DIRTY.value],
            out_of_order_rooms=by_status[RoomStatus.OUT_OF_ORDER.value],
            in_house_bookings=count_bookings(Booking.status == BookingStatus.CHECKED_IN),
            arrivals_pending=count_bookings(Booking.status == BookingStatus.CONFIRMED,
                                            Booking.check_in == today),
            # <= hôm nay: tính cả khách quá hạn trả phòng mà chưa check-out
            departures_pending=count_bookings(Booking.status == BookingStatus.CHECKED_IN,
                                              Booking.check_out <= today),
            occupancy_pct=_ratio(tonight[0], sellable, 100),
            room_revenue_today=_round(tonight[1]),
            service_revenue_today=_round(sum((x for _, x in service_today), ZERO)))

    # ------------------------------------------------------- helper
    def _validate_range(self, from_date: dt.date, to_date: dt.date) -> list[dt.date]:
        if to_date < from_date:
            raise BusinessError("Ngày kết thúc không được trước ngày bắt đầu",
                                code="INVALID_DATE_RANGE")
        days = _days(from_date, to_date)
        if len(days) > MAX_REPORT_DAYS:
            raise BusinessError(f"Báo cáo tối đa {MAX_REPORT_DAYS} ngày mỗi lần",
                                code="DATE_RANGE_TOO_LONG")
        return days

    def _sellable_room_count(self) -> int:
        return self.db.scalar(select(func.count(Room.id)).where(
            Room.status != RoomStatus.OUT_OF_ORDER))

    def _night_rates_query(self, from_date, to_date):
        """Các đêm-phòng ĐÃ BÁN trong kỳ (booking CheckedIn/CheckedOut)."""
        return (select(BookingNightRate.id)
                .join(BookingDetail, BookingDetail.id == BookingNightRate.booking_detail_id)
                .join(Booking, Booking.id == BookingDetail.booking_id)
                .where(Booking.status.in_([s.value for s in REVENUE_STATUSES]),
                       Booking.deleted_at.is_(None),
                       BookingNightRate.date >= from_date,
                       BookingNightRate.date <= to_date))

    def _room_nights_by_date(self, from_date, to_date) -> dict[dt.date, tuple[int, Decimal]]:
        """{ngày: (số đêm-phòng bán, doanh thu phòng)} — MỘT truy vấn GROUP BY."""
        stmt = (self._night_rates_query(from_date, to_date)
                .with_only_columns(BookingNightRate.date, func.count(BookingNightRate.id),
                                   func.sum(BookingNightRate.price))
                .group_by(BookingNightRate.date))
        return {day: (count, Decimal(total or 0)) for day, count, total in self.db.execute(stmt)}

    def _service_revenue_query(self, from_date, to_date, group_column):
        """Doanh thu dịch vụ (giá đã chốt × số lượng) gom theo group_column."""
        return (select(group_column,
                       func.sum(BookingServiceLine.unit_price * BookingServiceLine.quantity))
                .join(Booking, Booking.id == BookingServiceLine.booking_id)
                .where(Booking.status.in_([s.value for s in REVENUE_STATUSES]),
                       Booking.deleted_at.is_(None),
                       BookingServiceLine.used_date >= from_date,
                       BookingServiceLine.used_date <= to_date)
                .group_by(group_column))
