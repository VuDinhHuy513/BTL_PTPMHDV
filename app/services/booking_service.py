"""Đặt phòng, nhận phòng, trả phòng. Xem R4 → R8.

Test tương ứng: tests/test_booking_flow.py
"""
import datetime as dt

from sqlalchemy.orm import Session

from app.models.enums import BookingStatus

# Vòng đời hợp lệ của booking — xem sơ đồ ở R4.
# Gom vào một chỗ thay vì rải if khắp nơi.
ALLOWED_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.PENDING: {BookingStatus.CONFIRMED, BookingStatus.CANCELLED},
    BookingStatus.CONFIRMED: {BookingStatus.CHECKED_IN, BookingStatus.CANCELLED,
                              BookingStatus.NO_SHOW},
    BookingStatus.CHECKED_IN: {BookingStatus.CHECKED_OUT},
    BookingStatus.CHECKED_OUT: set(),
    BookingStatus.CANCELLED: set(),
    BookingStatus.NO_SHOW: set(),
}

MAX_NIGHTS_PER_BOOKING = 60      # hằng số có tên, không viết số 60 giữa code


class BookingService:
    def __init__(self, db: Session, current_user_id: int | None = None) -> None:
        self.db = db
        self.current_user_id = current_user_id
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
          expire_on_commit=False, nếu không ép nạp lại thì quan hệ vừa gán
          ở check-in sẽ vẫn đọc ra None.
        """
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------- CREATE
    def create(self, dto):
        """Tạo booking. ĐÂY LÀ HÀM QUAN TRỌNG NHẤT CỦA ĐỒ ÁN.

        TODO — các bước:
          1. Xác định customer_id (đã có sẵn, hoặc tạo mới từ dto.customer).
          2. Sắp xếp dto.lines theo room_type_id TĂNG DẦN  ← tránh deadlock.
          3. Mở khóa cho từng loại phòng (contextlib.ExitStack + room_type_lock).
          4. TRONG khóa: đếm lại phòng trống cho từng loại.
             Thiếu → BusinessError code ROOM_NOT_AVAILABLE.
          5. Tạo Booking + BookingDetail, mỗi detail gắn BookingNightRate
             với giá CHỐT lấy từ PricingService.
          6. db.add, db.flush, ghi AuditLog, db.commit.

        ⚠ Bước 4 phải nằm TRONG khóa. Nếu đếm trước rồi mới khóa thì vô nghĩa.
        ⚠ room_id để None — phòng vật lý chỉ gán lúc check-in.

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
        """Sửa ngày ở. Xem R6.

        TODO:
          - Chỉ cho sửa khi Pending hoặc Confirmed.
          - Khóa, kiểm tra phòng trống cho ngày MỚI, nhớ truyền
            exclude_booking_id=booking.id  ← nếu không sẽ tự chặn chính mình.
          - Xóa BookingNightRate cũ, tạo lại theo bảng giá hiện hành.
        """
        raise NotImplementedError("TODO")

    # --------------------------------------------- CHUYỂN TRẠNG THÁI
    def confirm(self, booking_id: int):
        raise NotImplementedError("TODO")

    def cancel(self, booking_id: int, reason: str):
        """Hủy booking. Xem R10.

        TODO: tính hoàn cọc theo settings.CANCEL_FREE_BEFORE_DAYS.
        KHÔNG xóa bản ghi, chỉ đổi status sang Cancelled.
        """
        raise NotImplementedError("TODO")

    def no_show(self, booking_id: int):
        raise NotImplementedError("TODO")

    # ----------------------------------------------------------- CHECK-IN
    def check_in(self, booking_id: int, dto):
        """Nhận phòng. Xem R7.

        TODO — các bước:
          1. _ensure_transition sang CHECKED_IN.
          2. Chưa đến ngày nhận phòng → BusinessError TOO_EARLY_TO_CHECK_IN.
          3. Với mỗi BookingDetail, gán một Room cụ thể:
               - lễ tân chỉ định trong dto.assignments, HOẶC
               - hệ thống tự lấy phòng trống đầu tiên
             Kiểm tra phòng: đúng loại, không bảo trì, đã dọn sạch,
             chưa có khách khác trong khoảng ngày.
          4. Đổi Room.status sang OCCUPIED.
          5. Ghi id_card_number, cập nhật deposit.
          6. Booking.status = CHECKED_IN, ghi checked_in_at.
        """
        raise NotImplementedError("TODO")

    def walk_in(self, dto):
        """Khách vãng lai. TODO: gọi create() rồi gọi check_in() ngay.

        Đừng viết lại logic — tái sử dụng hai hàm đã có.
        """
        raise NotImplementedError("TODO")

    def change_room(self, booking_id: int, detail_id: int, new_room_id: int,
                    reason: str | None = None):
        """TODO: phòng cũ → Dirty + tạo task dọn, phòng mới → Occupied."""
        raise NotImplementedError("TODO")

    # ---------------------------------------------------------- CHECK-OUT
    def check_out(self, booking_id: int):
        """Trả phòng. Xem R8.

        TODO:
          1. _ensure_transition sang CHECKED_OUT.
          2. Gọi FolioService(...).issue_invoice(booking).
             ⚠ ĐỪNG tính tiền lại ở đây — logic tính tiền nằm ở FolioService.
          3. Mỗi phòng → Dirty, tạo HousekeepingTask.
          4. Booking.status = CHECKED_OUT, ghi checked_out_at.
        """
        raise NotImplementedError("TODO")

    def soft_delete(self, booking_id: int) -> None:
        """TODO: set deleted_at, KHÔNG db.delete()."""
        raise NotImplementedError("TODO")
