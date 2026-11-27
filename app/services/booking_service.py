"""Đặt phòng, nhận phòng, trả phòng. Xem R4 → R8, R10.

Booking do NHÂN VIÊN tạo (khách gọi điện hoặc đến quầy): nhân viên chọn đúng phòng
(room_ids) ngay lúc đặt. Khách cũng có thể tự đặt không cần đăng nhập (R13): khách chỉ
chọn loại phòng, hệ thống tự gán phòng rồi gọi lại create() — không viết khóa thứ hai.

Test tương ứng: tests/test_booking_flow.py
"""
import datetime as dt
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessError, NotFoundError
from app.db.locking import lock_booking, lock_rooms
from app.models import (Booking, BookingDetail, BookingNightRate, BookingSource,
                        BookingStatus, Customer, Room, RoomStatus)
from app.schemas.common import DEFAULT_PAGE_LIMIT
from app.services.availability_service import AvailabilityService
from app.services.folio_service import FolioService
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

# Booking đã gắn với khách thật trong phòng / tiền / hóa đơn thì không được xóa
UNDELETABLE_STATUSES = (BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT)

# Đổi phòng được khi chưa đến hoặc đang ở (R7)
ROOM_CHANGEABLE_STATUSES = (BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN)

NOTE_MAX_LENGTH = 500            # = độ dài cột bookings.note


def _append_note(note: str | None, line: str) -> str:
    """Ghi thêm một dòng vào ghi chú booking (lưu lại lịch sử đổi phòng).

    Quá độ dài cột thì bỏ bớt phần CŨ NHẤT ở đầu, giữ các dòng mới nhất.
    """
    text = f"{note}\n{line}" if note else line
    return text[-NOTE_MAX_LENGTH:]


# Để ngoài class: trong class có hàm tên `list`, viết `list[Room]` bên dưới
# hàm đó thì Python hiểu `list` là hàm chứ không phải kiểu list
def _check_capacity(rooms: list[Room], guests: int) -> None:
    if guests > sum(r.room_type.capacity for r in rooms):
        raise BusinessError("Số khách vượt quá tổng sức chứa các phòng đã chọn",
                            code="GUESTS_EXCEED_CAPACITY")


class BookingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pricing = PricingService(db)
        self.availability = AvailabilityService(db)

    # ------------------------------------------------------------- helper
    def _ensure_transition(self, booking, target: BookingStatus) -> None:
        """Chặn mọi bước chuyển không có trong sơ đồ R4."""
        current = BookingStatus(booking.status)
        if target not in ALLOWED_TRANSITIONS[current]:
            raise BusinessError(
                f"Không thể chuyển booking từ {current.value} sang {target.value}",
                code="INVALID_STATUS_TRANSITION")

    def _lock_booking(self, booking_id: int) -> None:
        """Khóa dòng booking trước khi đổi trạng thái. Xem lock_booking ở db/locking.py."""
        lock_booking(self.db, booking_id)

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
        rooms = self._check_rooms_free(room_ids, check_in, check_out, exclude_booking_id)
        _check_capacity(rooms, guests)
        return rooms

    def _check_rooms_free(self, room_ids: list[int], check_in: dt.date,
                          check_out: dt.date,
                          exclude_booking_id: int | None = None) -> list[Room]:
        """Phòng tồn tại, không bảo trì, không bị booking khác chiếm. Gọi SAU khi khóa."""
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
        try:
            booking = self._create_uncommitted(dto, source)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._load(booking.id)

    def _create_uncommitted(self, dto, source: BookingSource) -> Booking:
        """Lõi của create(): khóa, kiểm tra, ghi — nhưng CHƯA commit.

        Tách riêng để walk_in() gộp "tạo + nhận phòng" vào một giao dịch.
        """
        room_ids = sorted(dto.room_ids)          # khóa theo id tăng dần, tránh deadlock
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
        return booking

    # --------------------------------------------------------------- READ
    def get(self, booking_id: int) -> Booking:
        return self._load(booking_id)

    def get_by_code(self, code: str) -> Booking:
        booking_id = self.db.scalar(
            select(Booking.id).where(Booking.code == code, Booking.deleted_at.is_(None)))
        if booking_id is None:
            raise NotFoundError("Booking", code)
        return self._load(booking_id)

    def list(self, *, status: BookingStatus | None = None,
             from_date: dt.date | None = None, to_date: dt.date | None = None,
             customer_id: int | None = None, page: int = 1,
             limit: int = DEFAULT_PAGE_LIMIT) -> tuple[list[Booking], int]:
        """Danh sách booking có lọc + phân trang. Trả về (danh_sách, tổng_số).

        from/to lọc theo kỳ ở GIAO NHAU với [from_date, to_date) — cùng công
        thức < và > của R3. Ví dụ hỏi "booking nào có khách ở trong tuần này"
        thì booking đến từ tuần trước nhưng còn ở sang tuần này vẫn hiện ra.
        """
        conditions = [Booking.deleted_at.is_(None)]       # không hiện booking đã xóa mềm
        if status is not None:
            conditions.append(Booking.status == status)
        if customer_id is not None:
            conditions.append(Booking.customer_id == customer_id)
        if to_date is not None:
            conditions.append(Booking.check_in < to_date)
        if from_date is not None:
            conditions.append(Booking.check_out > from_date)

        # Đếm tổng trên CÙNG điều kiện lọc, nhưng không phân trang
        total = self.db.scalar(select(func.count(Booking.id)).where(*conditions))

        stmt = (select(Booking).where(*conditions)
                .options(selectinload(Booking.customer),
                         selectinload(Booking.details).selectinload(BookingDetail.room),
                         selectinload(Booking.details).selectinload(BookingDetail.night_rates))
                # id làm tiêu chí phụ: hai booking cùng created_at vẫn có thứ tự cố định,
                # không thì chuyển trang có thể lặp/mất dòng
                .order_by(Booking.created_at.desc(), Booking.id.desc())
                .offset((page - 1) * limit).limit(limit))
        return list(self.db.scalars(stmt).all()), total

    # ------------------------------------------------------------- UPDATE
    def update(self, booking_id: int, dto) -> Booking:
        """Sửa ngày ở / số khách / ghi chú. Xem R6.

        Đổi ngày → kiểm tra lại phòng trống (loại trừ chính booking này) và
        chốt lại giá từng đêm theo base_price HIỆN HÀNH.
        Chỉ đổi số khách / ghi chú → giữ nguyên giá đã chốt, chỉ kiểm sức chứa.
        Muốn đổi sang phòng khác thì dùng change_room, không sửa ở đây.
        """
        try:
            self._lock_booking(booking_id)
            booking = self._load(booking_id)
            if booking.status != BookingStatus.CONFIRMED:
                raise BusinessError("Chỉ sửa được booking đang ở trạng thái Confirmed",
                                    code="BOOKING_NOT_EDITABLE")

            dates_changed = (dto.check_in, dto.check_out) != (booking.check_in,
                                                                booking.check_out)
            if dates_changed:
                self._reschedule(booking, dto)
            else:
                _check_capacity([d.room for d in booking.details], dto.guests)

            booking.guests = dto.guests
            booking.note = dto.note
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._load(booking_id)

    def _reschedule(self, booking: Booking, dto) -> None:
        """Đổi ngày ở: khóa phòng, kiểm tra trống, chốt lại giá. Chưa commit."""
        # Chỉ chặn ngày quá khứ khi check_in thật sự đổi: khách đến muộn (check_in
        # đã qua mà vẫn Confirmed) vẫn phải sửa được ngày đi.
        if dto.check_in != booking.check_in and dto.check_in < dt.date.today():
            raise BusinessError("Không được dời ngày nhận phòng về quá khứ",
                                code="CHECK_IN_IN_PAST")

        room_ids = sorted(d.room_id for d in booking.details)
        lock_rooms(self.db, room_ids)
        # exclude_booking_id: không có nó thì các đêm cũ của CHÍNH booking này bị
        # coi là "đã chiếm" → dời 1 ngày cũng báo hết phòng
        self._check_rooms_bookable(room_ids, dto.check_in, dto.check_out,
                                   dto.guests, exclude_booking_id=booking.id)

        for detail in booking.details:
            # Xóa giá cũ và flush TRƯỚC khi thêm giá mới: nếu không, các đêm
            # trùng ngày đụng ràng buộc unique (booking_detail_id, date)
            detail.night_rates.clear()
        self.db.flush()
        for detail in booking.details:
            rates = self.pricing.get_nightly_rates(
                detail.room.room_type_id, dto.check_in, dto.check_out)
            detail.night_rates.extend(BookingNightRate(date=d, price=p) for d, p in rates)

        booking.check_in = dto.check_in
        booking.check_out = dto.check_out

    # --------------------------------------------- CHUYỂN TRẠNG THÁI
    def cancel(self, booking_id: int, reason: str) -> Booking:
        """Hủy booking. Xem R10.

        Chỉ khi Confirmed. KHÔNG xóa bản ghi — chỉ đổi status, để báo cáo vẫn
        thấy booking đã hủy. Không cần "nhả phòng" bằng tay: Cancelled không
        nằm trong BLOCKING_STATUSES nên tra phòng trống tự bỏ qua booking này.
        """
        try:
            self._lock_booking(booking_id)
            booking = self._load(booking_id)
            self._ensure_transition(booking, BookingStatus.CANCELLED)
            booking.status = BookingStatus.CANCELLED
            booking.cancel_reason = reason
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._load(booking_id)

    def no_show(self, booking_id: int) -> Booking:
        """Khách không đến. Xem R10.

        Chỉ khi Confirmed và đã tới ngày nhận phòng: chưa tới ngày thì khách
        vẫn còn có thể đến, đánh NoShow là sai. Phòng tự được nhả như cancel.
        """
        try:
            self._lock_booking(booking_id)
            booking = self._load(booking_id)
            self._ensure_transition(booking, BookingStatus.NO_SHOW)
            if dt.date.today() < booking.check_in:
                raise BusinessError(
                    f"Chưa tới ngày nhận phòng ({booking.check_in:%d/%m/%Y}), "
                    "chưa thể đánh khách không đến",
                    code="TOO_EARLY_TO_NO_SHOW")
            booking.status = BookingStatus.NO_SHOW
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._load(booking_id)

    # ----------------------------------------------------------- CHECK-IN
    def check_in(self, booking_id: int, id_card_number: str | None = None) -> Booking:
        """Nhận phòng. Xem R7. Phòng đã chọn từ lúc đặt nên KHÔNG có bước gán."""
        try:
            self._lock_booking(booking_id)
            self._check_in_uncommitted(booking_id, id_card_number)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._load(booking_id)

    def _check_in_uncommitted(self, booking_id: int, id_card_number: str | None) -> None:
        """Lõi của check_in(), CHƯA commit — walk_in() dùng lại."""
        # Khóa phòng TRƯỚC khi đọc trạng thái phòng: tránh lúc vừa kiểm "Available"
        # thì người khác PATCH phòng sang OutOfOrder
        lock_rooms(self.db, list(self.db.scalars(
            select(BookingDetail.room_id).where(BookingDetail.booking_id == booking_id))))
        booking = self._load(booking_id)          # nạp SAU khóa → trạng thái phòng mới nhất

        self._ensure_transition(booking, BookingStatus.CHECKED_IN)
        today = dt.date.today()
        if today < booking.check_in:
            raise BusinessError(
                f"Chưa tới ngày nhận phòng ({booking.check_in:%d/%m/%Y})",
                code="TOO_EARLY_TO_CHECK_IN")
        # Đến muộn vẫn nhận được (R7), nhưng qua cả ngày trả phòng thì kỳ ở đã hết
        if today >= booking.check_out:
            raise BusinessError("Đã qua ngày trả phòng, không thể nhận phòng",
                                code="STAY_ALREADY_ENDED")

        for detail in booking.details:
            if detail.room.status != RoomStatus.AVAILABLE:
                raise BusinessError(
                    f"Phòng {detail.room.room_number} đang "
                    f"{RoomStatus(detail.room.status).value}, chưa nhận khách được "
                    "(dọn phòng xong hoặc dùng đổi phòng)",
                    code="ROOM_NOT_READY")

        if id_card_number:
            booking.customer.id_card_number = id_card_number
        for detail in booking.details:
            detail.room.status = RoomStatus.OCCUPIED
        booking.status = BookingStatus.CHECKED_IN
        booking.checked_in_at = dt.datetime.now()

    def walk_in(self, dto) -> Booking:
        """Khách vãng lai: tạo booking (check_in = hôm nay) rồi nhận phòng luôn.

        Dùng lại lõi của create() và check_in(), không viết lại logic. Commit
        MỘT lần ở cuối: check-in lỗi (ví dụ phòng đang Dirty) thì booking vừa
        tạo cũng bị rollback, không để lại booking Confirmed "mồ côi".
        """
        try:
            booking = self._create_uncommitted(dto, BookingSource.STAFF)
            self._check_in_uncommitted(booking.id, dto.id_card_number)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._load(booking.id)

    def change_room(self, booking_id: int, detail_id: int, new_room_id: int,
                    reason: str | None = None) -> Booking:
        """Đổi phòng. Dùng được khi booking Confirmed hoặc CheckedIn. Xem R7.

        Chỉ đổi cho các đêm CÒN LẠI: từ hôm nay (hoặc từ check_in nếu chưa tới).
        Đêm đã qua giữ nguyên giá đã chốt.
        """
        try:
            self._lock_booking(booking_id)
            booking = self._load(booking_id)
            status = BookingStatus(booking.status)
            if status not in ROOM_CHANGEABLE_STATUSES:
                raise BusinessError(f"Booking đang {status.value}, không đổi phòng được",
                                    code="ROOM_CHANGE_NOT_ALLOWED")

            detail = next((d for d in booking.details if d.id == detail_id), None)
            if detail is None:
                raise NotFoundError("BookingDetail", detail_id)
            if new_room_id in {d.room_id for d in booking.details}:
                # Kiểm tra phòng trống bên dưới loại trừ chính booking này nên
                # không bắt được trường hợp này — phải chặn riêng
                raise BusinessError("Phòng mới đã nằm trong booking này",
                                    code="ROOM_ALREADY_IN_BOOKING")

            start = max(dt.date.today(), booking.check_in)
            if start >= booking.check_out:
                raise BusinessError("Booking không còn đêm nào để đổi phòng",
                                    code="NO_REMAINING_NIGHTS")

            old_room = detail.room
            lock_rooms(self.db, [old_room.id, new_room_id])
            [new_room] = self._check_rooms_free(
                [new_room_id], start, booking.check_out, exclude_booking_id=booking.id)
            other_rooms = [d.room for d in booking.details if d.id != detail_id]
            _check_capacity(other_rooms + [new_room], booking.guests)

            if status == BookingStatus.CHECKED_IN:
                if new_room.status != RoomStatus.AVAILABLE:
                    raise BusinessError(
                        f"Phòng {new_room.room_number} chưa sẵn sàng nhận khách",
                        code="ROOM_NOT_READY")
                old_room.status = RoomStatus.DIRTY      # khách vừa rời phòng cũ
                new_room.status = RoomStatus.OCCUPIED

            if new_room.room_type_id != old_room.room_type_id:
                self._reprice_from(detail, new_room.room_type_id, start, booking.check_out)
            detail.room = new_room
            booking.note = _append_note(booking.note, (
                f"[{dt.date.today():%d/%m/%Y}] Đổi phòng {old_room.room_number} → "
                f"{new_room.room_number}" + (f": {reason}" if reason else "")))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        # _load có populate_existing → room_number trả về là phòng MỚI
        return self._load(booking_id)

    def _reprice_from(self, detail: BookingDetail, room_type_id: int,
                      start: dt.date, check_out: dt.date) -> None:
        """Chốt lại giá các đêm từ `start` theo loại phòng mới; đêm trước giữ nguyên."""
        for rate in [r for r in detail.night_rates if r.date >= start]:
            detail.night_rates.remove(rate)
        self.db.flush()                 # xóa trước, tránh trùng unique (detail_id, date)
        detail.night_rates.extend(
            BookingNightRate(date=d, price=p)
            for d, p in self.pricing.get_nightly_rates(room_type_id, start, check_out))

    # ---------------------------------------------------------- CHECK-OUT
    def check_out(self, booking_id: int):
        """Trả phòng + xuất hóa đơn. Xem R8. Trả về InvoiceOut để in.

        KHÔNG bắt trả đủ tiền mới cho trả phòng: thu tiền làm bên ngoài hệ thống
        (tiền mặt / chuyển khoản), hóa đơn vẫn ghi số đã trả và số còn lại.
        Trả phòng sớm vẫn tính đủ các đêm đã đặt (R10) — không tính lại.
        """
        folio_service = FolioService(self.db)
        try:
            self._lock_booking(booking_id)
            booking = self._load(booking_id)
            self._ensure_transition(booking, BookingStatus.CHECKED_OUT)

            # Tính tiền nằm ở FolioService, không tính lại ở đây
            invoice = folio_service.issue_invoice(booking)
            for detail in booking.details:
                # Lễ tân gọi buồng phòng ngoài hệ thống; dọn xong thì
                # PATCH /rooms/{id}/status về Available
                detail.room.status = RoomStatus.DIRTY
            booking.status = BookingStatus.CHECKED_OUT
            booking.checked_out_at = dt.datetime.now()
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return folio_service.get_invoice(invoice.id)

    def soft_delete(self, booking_id: int) -> None:
        """Xóa mềm: ghi deleted_at, KHÔNG db.delete() — giữ dữ liệu cho báo cáo.

        Dùng để dọn booking nhập nhầm. Chặn khi khách đang ở (CheckedIn: phòng
        đang Occupied mà mất booking thì không ai trả phòng được) hoặc đã trả
        (CheckedOut: đã có hóa đơn, tiền). Booking xóa mềm không còn chiếm phòng
        vì mọi truy vấn đều lọc deleted_at IS NULL.
        """
        try:
            self._lock_booking(booking_id)
            booking = self._load(booking_id)
            if booking.status in UNDELETABLE_STATUSES:
                raise BusinessError(
                    f"Booking đang {BookingStatus(booking.status).value}, không xóa được",
                    code="BOOKING_NOT_DELETABLE")
            booking.deleted_at = dt.datetime.now()
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
