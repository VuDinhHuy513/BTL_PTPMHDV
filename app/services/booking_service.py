"""Đặt phòng, nhận phòng, trả phòng. Xem R4 → R8, R10.

Booking do NHÂN VIÊN tạo (khách gọi điện hoặc đến quầy), không có khách tự đặt.
Nhân viên chọn đúng phòng (room_ids) ngay lúc đặt.

Test tương ứng: tests/test_booking_flow.py
"""
import datetime as dt

from sqlalchemy.orm import Session

from app.models.enums import BookingStatus

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
        # TODO: khởi tạo PricingService, AvailabilityService

    # ------------------------------------------------------------- helper
    def _ensure_transition(self, booking, target: BookingStatus) -> None:
        """TODO: nếu target không nằm trong ALLOWED_TRANSITIONS[hiện tại]
        thì raise BusinessError code INVALID_STATUS_TRANSITION."""
        raise NotImplementedError("TODO")

    def _load(self, booking_id: int):
        """TODO: nạp booking kèm details, night_rates, room, customer.

        Dùng selectinload để tránh N+1 query.
        Không tìm thấy hoặc deleted_at != NULL → NotFoundError.

        ⚠ Thêm .execution_options(populate_existing=True). Session dùng
          expire_on_commit=False, nếu không ép nạp lại thì quan hệ vừa đổi
          ở change_room sẽ vẫn đọc ra phòng cũ.
        """
        raise NotImplementedError("TODO")

    def _resolve_customer(self, dto):
        """TODO: dto.customer_id có thì nạp khách đó (không thấy → NotFoundError).

        Không thì tìm Customer theo dto.customer.phone: có rồi thì dùng lại
        (không tạo mới), chưa có mới tạo. Nhờ vậy lịch sử đặt phòng của một
        khách nằm chung một chỗ."""
        raise NotImplementedError("TODO")

    def _check_rooms_bookable(self, room_ids: list[int], check_in: dt.date,
                              check_out: dt.date, guests: int,
                              exclude_booking_id: int | None = None):
        """Gọi SAU KHI đã khóa phòng (lock_rooms). TODO:
          - Nạp các Room; thiếu id nào → NotFoundError.
          - Phòng OutOfOrder → BusinessError ROOM_NOT_AVAILABLE.
          - Phòng nằm trong AvailabilityService._busy_room_ids(...)
            → BusinessError ROOM_NOT_AVAILABLE (nêu số phòng trong message).
          - guests > tổng capacity các phòng → BusinessError GUESTS_EXCEED_CAPACITY.
        Trả về danh sách Room để dùng tiếp."""
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------- CREATE
    def create(self, dto):
        """Tạo booking. ĐÂY LÀ HÀM QUAN TRỌNG NHẤT CỦA ĐỒ ÁN.

        TODO — các bước:
          1. Xác định khách qua _resolve_customer.
          2. Sắp dto.room_ids theo TĂNG DẦN  ← tránh deadlock.
          3. lock_rooms(db, room_ids): SELECT ... FOR UPDATE các phòng đó
             (xem app/db/locking.py). Khóa nhả khi commit.
          4. TRONG khóa: _check_rooms_bookable — phòng có còn trống không.
             Sai → BusinessError ROOM_NOT_AVAILABLE.
          5. Tạo Booking (status = CONFIRMED) + mỗi phòng một BookingDetail,
             gắn BookingNightRate với giá CHỐT lấy từ PricingService theo
             loại của phòng đó.
          6. db.add, db.flush, db.commit.

        ⚠ Bước 4 phải nằm SAU khi đã khóa. Nếu kiểm tra trước rồi mới khóa
          thì vô nghĩa.

        Kiểm chứng bằng: python -m scripts.test_concurrent
        """
        raise NotImplementedError("TODO: xem docstring ở trên")

    # --------------------------------------------------------------- READ
    def get(self, booking_id: int):
        raise NotImplementedError("TODO")

    def get_by_code(self, code: str):
        raise NotImplementedError("TODO")

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
