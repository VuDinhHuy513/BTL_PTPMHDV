"""Folio = sổ ghi nợ của booking: tiền phòng + dịch vụ + thuế − đã trả. Xem R9.

Đã viết (bước 6): list_services, add_service, remove_service.

TODO (bước 7) — các hàm còn lại:

    build(booking) -> FolioOut
        Duyệt booking.details → cộng night_rates thành room_charge, mỗi đêm
        là một dòng trong folio.
        Duyệt booking_services → service_charge.
        subtotal = room_charge + service_charge
        vat_amount = subtotal * settings.VAT_RATE   ← KHÔNG viết 0.08
        total = subtotal + vat_amount
        paid = tổng payments (số dương là thu, số âm là hoàn)
        balance_due = total - paid

    add_payment(booking, amount, method, note)

    refund(payment_id, amount, reason)
        Tạo Payment với amount ÂM. Không sửa bản ghi cũ.

    issue_invoice(booking) -> Invoice
        Đã có hóa đơn rồi thì trả về cái cũ, không tạo trùng.
        Lưu cả vat_rate vào hóa đơn.
"""
import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessError, NotFoundError
from app.db.locking import lock_booking
from app.models import Booking, BookingStatus, Service
# Model trùng tên với class BookingService (app/services/booking_service.py)
# → đặt bí danh để đọc code không nhầm hai thứ với nhau
from app.models import BookingService as BookingServiceLine


class FolioService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------- DỊCH VỤ
    def list_services(self, booking_id: int) -> list[BookingServiceLine]:
        self._get_booking(booking_id)            # booking không có → 404
        stmt = (select(BookingServiceLine)
                .where(BookingServiceLine.booking_id == booking_id)
                .options(selectinload(BookingServiceLine.service))
                .order_by(BookingServiceLine.used_date, BookingServiceLine.id))
        return list(self.db.scalars(stmt).all())

    def add_service(self, booking_id: int, dto) -> BookingServiceLine:
        """Ghi nhận khách dùng dịch vụ. CHỐT unit_price từ danh mục ngay lúc này."""
        try:
            # Khóa booking: không khóa thì thêm dịch vụ đúng lúc người khác bấm
            # check-out → dòng dịch vụ lọt ra ngoài hóa đơn
            lock_booking(self.db, booking_id)
            booking = self._get_booking(booking_id)
            self._ensure_in_house(booking)

            used_date = dto.used_date or dt.date.today()
            if not booking.check_in <= used_date <= dt.date.today():
                raise BusinessError(
                    "Ngày dùng dịch vụ phải từ ngày nhận phòng đến hôm nay",
                    code="INVALID_USED_DATE")

            service = self.db.get(Service, dto.service_id)
            if not service:
                raise NotFoundError("Service", dto.service_id)

            line = BookingServiceLine(
                booking_id=booking.id, service_id=service.id, quantity=dto.quantity,
                used_date=used_date, note=dto.note,
                unit_price=service.unit_price)   # ← chốt giá (CONVENTIONS mục 4)
            self.db.add(line)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._get_line(booking_id, line.id)

    def remove_service(self, booking_id: int, line_id: int) -> None:
        """Xóa dòng ghi nhầm. Xóa thật (không xóa mềm): dòng chưa vào hóa đơn nào
        vì chỉ xóa được khi khách còn đang ở."""
        try:
            lock_booking(self.db, booking_id)
            booking = self._get_booking(booking_id)
            self._ensure_in_house(booking)
            self.db.delete(self._get_line(booking_id, line_id))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    # ------------------------------------------------------- helper
    def _get_booking(self, booking_id: int) -> Booking:
        booking = self.db.scalar(select(Booking).where(
            Booking.id == booking_id, Booking.deleted_at.is_(None)))
        if not booking:
            raise NotFoundError("Booking", booking_id)
        return booking

    def _get_line(self, booking_id: int, line_id: int) -> BookingServiceLine:
        # Lọc thêm booking_id: chặn xóa dòng của booking KHÁC qua URL booking này
        line = self.db.scalar(
            select(BookingServiceLine)
            .where(BookingServiceLine.id == line_id,
                   BookingServiceLine.booking_id == booking_id)
            .options(selectinload(BookingServiceLine.service)))
        if not line:
            raise NotFoundError("BookingService", line_id)
        return line

    @staticmethod
    def _ensure_in_house(booking: Booking) -> None:
        """Chỉ ghi/xóa dịch vụ khi khách ĐANG Ở. Chưa đến thì chưa dùng được;
        đã trả phòng thì hóa đơn đã xuất, thêm/xóa nữa là lệch hóa đơn."""
        if booking.status != BookingStatus.CHECKED_IN:
            raise BusinessError(
                f"Booking đang {BookingStatus(booking.status).value}, chỉ ghi "
                "dịch vụ khi khách đang ở (CheckedIn)",
                code="BOOKING_NOT_IN_HOUSE")
