"""Đặt phòng, nhận phòng, trả phòng. Xem R4 → R8, R10.

Booking do NHÂN VIÊN tạo (khách gọi điện hoặc đến quầy): nhân viên chọn đúng phòng
(room_ids) ngay lúc đặt. Khách cũng có thể tự đặt không cần đăng nhập (R13): khách chỉ
chọn loại phòng, hệ thống tự gán phòng rồi gọi lại create() — không viết khóa thứ hai.

Test tương ứng: tests/test_booking_flow.py
"""
import datetime as dt
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessError, NotFoundError
from app.db.locking import lock_rooms
from app.models import (Booking, BookingDetail, BookingNightRate, BookingSource,
                        BookingStatus, Customer, Room, RoomStatus)
from app.services.availability_service import AvailabilityService
from app.services.pricing_service import PricingService

# Vòng đời hợp lệ của booking — xem sơ đồ ở R4.
# Gom vào một chỗ thay vì rải if khắp nơi.
ALLOWED_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.CONFIRMED: {BookingStatus.CHECKED_IN, BookingStatus.CANCELLED,
                              BookingStatus.NO_SHOW},
    BookingStatus.CHECKED_IN: {BookingStatus.CHECKED_OUT},
    BookingStatus.CHECKED_OUT: set(),
    BookingStatus.CANCELLED: set(),
    BookingStatus.NO_SHOW: set(),
}

MAX_NIGHTS_PER_BOOKING = 60      # hằng số có tên, không viết số 60 giữa code


class BookingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pricing = PricingService(db)
        self.availability = AvailabilityService(db)

    # ------------------------------------------------------------- helper
    def _ensure_transition(self, booking, target: BookingStatus) -> None:
        """TODO: nếu target không nằm trong ALLOWED_TRANSITIONS[hiện tại]
        thì raise BusinessError code INVALID_STATUS_TRANSITION."""
        raise NotImplementedError("TODO")

    def _load(self, booking_id: int) -> Booking:
        """Nạp booking kèm details, night_rates, room, customer (selectinload, tránh N+1).

        populate_existing: Session dùng expire_on_commit=False, nếu không ép nạp
        lại thì quan hệ vừa đổi (ví dụ change_room) vẫn đọc ra phòng cũ.
        """
        stmt = (select(Booking)
                .where(Booking.id == booking_id, Booking.deleted_at.is_(None))
                .options(selectinload(Booking.customer),
                         selectinload(Booking.details).selectinload(BookingDetail.room),
                         selectinload(Booking.details).selectinload(BookingDetail.night_rates))
                .execution_options(populate_existing=True))
        booking = self.db.scalars(stmt).one_or_none()
        if not booking:
            raise NotFoundError("Booking", booking_id)
        return booking

    def _resolve_customer(self, dto) -> Customer:
        """Có customer_id thì nạp khách đó; không thì tìm theo số điện thoại.

        Số điện thoại đã có thì dùng lại khách cũ (không ghi đè thông tin),
        chưa có mới tạo. Nhờ vậy lịch sử đặt phòng của một khách nằm chung một chỗ.
        """
        if dto.customer_id is not None:
            customer = self.db.get(Customer, dto.customer_id)
            if not customer:
                raise NotFoundError("Customer", dto.customer_id)
            return customer

        info = dto.customer
        customer = self.db.scalars(
            select(Customer).where(Customer.phone == info.phone)
            .order_by(Customer.id).limit(1)).first()
        if customer:
            return customer
        customer = Customer(full_name=info.full_name, phone=info.phone,
                            email=info.email, id_card_number=info.id_card_number,
                            nationality=info.nationality)
        self.db.add(customer)
        self.db.flush()
        return customer

    def _check_rooms_bookable(self, room_ids: list[int], check_in: dt.date,
                              check_out: dt.date, guests: int,
                              exclude_booking_id: int | None = None) -> list[Room]:
        """Gọi SAU KHI đã khóa phòng (lock_rooms). Trả về danh sách Room."""
        rooms = list(self.db.scalars(
            select(Room).where(Room.id.in_(room_ids)).order_by(Room.id)).all())
        missing = set(room_ids) - {r.id for r in rooms}
        if missing:
            raise NotFoundError("Room", min(missing))

        busy = self.availability._busy_room_ids(check_in, check_out, exclude_booking_id)
        for room in rooms:
            if room.status == RoomStatus.OUT_OF_ORDER or room.id in busy:
                raise BusinessError(
                    f"Phòng {room.room_number} không còn trống trong khoảng ngày đã chọn",
                    code="ROOM_NOT_AVAILABLE")

        if guests > sum(r.room_type.capacity for r in rooms):
            raise BusinessError("Số khách vượt quá tổng sức chứa các phòng đã chọn",
                                code="GUESTS_EXCEED_CAPACITY")
        return rooms

    def _new_code(self) -> str:
        """Mã booking dạng BK251112-A1B2C3. Lặp lại nếu (rất hiếm) trùng."""
        while True:
            code = f"BK{dt.date.today():%y%m%d}-{secrets.token_hex(3).upper()}"
            if not self.db.scalar(select(Booking.id).where(Booking.code == code)):
                return code

    # ------------------------------------------------------------- CREATE
    def create(self, dto, source: BookingSource = BookingSource.STAFF) -> Booking:
        """Tạo booking. ĐÂY LÀ HÀM QUAN TRỌNG NHẤT CỦA ĐỒ ÁN.

        `source` do endpoint truyền vào (staff/online), không lấy từ dto.

        ⚠ lock_rooms phải chạy TRƯỚC mọi bước đọc dữ liệu nghiệp vụ (kiểm tra
          phòng, tra khách). Kiểm tra trước rồi mới khóa thì vô nghĩa.
        """
        room_ids = sorted(dto.room_ids)          # khóa theo id tăng dần, tránh deadlock
        try:
            lock_rooms(self.db, room_ids)
            rooms = self._check_rooms_bookable(
                room_ids, dto.check_in, dto.check_out, dto.guests)
            customer = self._resolve_customer(dto)

            booking = Booking(
                code=self._new_code(), customer_id=customer.id,
                check_in=dto.check_in, check_out=dto.check_out, guests=dto.guests,
                status=BookingStatus.CONFIRMED, source=source, note=dto.note)
            for room in rooms:
                # Chốt giá từng đêm theo loại của phòng này (R2)
                rates = self.pricing.get_nightly_rates(
                    room.room_type_id, dto.check_in, dto.check_out)
                booking.details.append(BookingDetail(
                    room_id=room.id,
                    night_rates=[BookingNightRate(date=d, price=p) for d, p in rates]))
            self.db.add(booking)
            self.db.flush()
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._load(booking.id)

    # --------------------------------------------------------------- READ
    def get(self, booking_id: int) -> Booking:
        return self._load(booking_id)

    def get_by_code(self, code: str) -> Booking:
        booking_id = self.db.scalar(
            select(Booking.id).where(Booking.code == code, Booking.deleted_at.is_(None)))
        if booking_id is None:
            raise NotFoundError("Booking", code)
        return self._load(booking_id)

    def list(self, *, status=None, from_date=None, to_date=None,
             customer_id=None, page: int = 1, limit: int = 20):
        """TODO: trả về (danh_sách, tổng_số) để endpoint dựng PageMeta."""
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------- UPDATE
    def update(self, booking_id: int, dto):
        """Sửa ngày ở / số khách / ghi chú. Xem R6.

        TODO:
          - Chỉ cho sửa khi Confirmed.
          - Khóa CHÍNH các phòng booking đang giữ, rồi _check_rooms_bookable
            cho ngày MỚI, nhớ truyền exclude_booking_id=booking.id
            ← nếu không sẽ tự chặn chính mình.
          - Xóa BookingNightRate cũ, tạo lại theo bảng giá hiện hành.
          - Muốn đổi sang phòng khác thì dùng change_room, không sửa ở đây.
        """
        raise NotImplementedError("TODO")

    # --------------------------------------------- CHUYỂN TRẠNG THÁI
    def cancel(self, booking_id: int, reason: str):
        """Hủy booking. Xem R10.

        TODO: chỉ khi Confirmed (không thì INVALID_STATUS_TRANSITION).
        Ghi cancel_reason, đổi status sang Cancelled. KHÔNG xóa bản ghi.
        Phòng được nhả cho MỌI đêm của booking vì Cancelled không chiếm phòng.
        """
        raise NotImplementedError("TODO")

    def no_show(self, booking_id: int):
        """Khách không đến. Xem R10.

        TODO: chỉ khi Confirmed. Hôm nay < check_in → BusinessError
        TOO_EARLY_TO_NO_SHOW. Đổi status sang NoShow, phòng được nhả.
        """
        raise NotImplementedError("TODO")

    # ----------------------------------------------------------- CHECK-IN
    def check_in(self, booking_id: int, dto):
        """Nhận phòng. Xem R7. Phòng đã chọn từ lúc đặt nên KHÔNG có bước gán.

        TODO — các bước:
          1. _ensure_transition sang CHECKED_IN.
          2. Hôm nay < check_in → BusinessError TOO_EARLY_TO_CHECK_IN.
          3. Mọi phòng của booking phải đang Available; phòng Dirty/Occupied/
             OutOfOrder → BusinessError ROOM_NOT_READY (lễ tân dùng change_room).
          4. Ghi id_card_number vào Customer (nếu có).
          5. Room.status = OCCUPIED cho từng phòng.
          6. Booking.status = CHECKED_IN, ghi checked_in_at.
        """
        raise NotImplementedError("TODO")

    def walk_in(self, dto):
        """Khách vãng lai. TODO: gọi create() (check_in = hôm nay) rồi check_in().

        Đừng viết lại logic — tái sử dụng hai hàm đã có. Cả hai phải nằm trong
        MỘT giao dịch: nếu check-in lỗi thì booking vừa tạo cũng không được lưu.
        """
        raise NotImplementedError("TODO")

    def change_room(self, booking_id: int, detail_id: int, new_room_id: int,
                    reason: str | None = None):
        """Đổi phòng. Dùng được khi booking Confirmed hoặc CheckedIn.

        TODO:
          - Khóa phòng mới; phòng mới phải trống cho các đêm còn lại
            (loại trừ chính booking) → không thì ROOM_NOT_AVAILABLE.
          - Confirmed: chỉ đổi detail.room_id.
          - CheckedIn: phòng cũ → Dirty, phòng mới phải Available rồi → Occupied.
          - Phòng mới khác loại/giá: tính lại giá các đêm CÒN LẠI (từ hôm nay),
            giữ nguyên giá các đêm đã qua.
        """
        raise NotImplementedError("TODO")

    # ---------------------------------------------------------- CHECK-OUT
    def check_out(self, booking_id: int):
        """Trả phòng. Xem R8.

        TODO:
          1. _ensure_transition sang CHECKED_OUT.
          2. Gọi FolioService(...).issue_invoice(booking).
             ⚠ ĐỪNG tính tiền lại ở đây — logic tính tiền nằm ở FolioService.
          3. Mỗi phòng → Dirty. Không tạo task dọn: lễ tân gọi buồng phòng
             ngoài hệ thống, dọn xong đổi phòng về Available bằng
             PATCH /rooms/{id}/status.
          4. Booking.status = CHECKED_OUT, ghi checked_out_at.
        """
        raise NotImplementedError("TODO")

    def soft_delete(self, booking_id: int) -> None:
        """TODO: set deleted_at, KHÔNG db.delete()."""
        raise NotImplementedError("TODO")
