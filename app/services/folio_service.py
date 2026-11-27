"""Folio = sổ ghi nợ của booking: tiền phòng + dịch vụ + thuế − đã trả. Xem R9.

    subtotal    = room_charge + service_charge    (đều là giá ĐÃ CHỐT)
    vat_amount  = subtotal × VAT_RATE             (settings, KHÔNG viết 0.08)
    total       = subtotal + vat_amount
    paid        = tổng payments (dương là thu, âm là hoàn)
    balance_due = total − paid

Hệ thống KHÔNG xử lý tiền thật và KHÔNG bắt trả đủ mới cho check-out: thu tiền
làm bên ngoài, payments chỉ là sổ ghi lại để biết ai còn nợ.
"""
import datetime as dt
import secrets
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.exceptions import BusinessError, NotFoundError
from app.db.locking import lock_booking
from app.models import (Booking, BookingDetail, BookingStatus, Invoice, Payment,
                        Room, Service)
# Model trùng tên với class BookingService (app/services/booking_service.py)
# → đặt bí danh để đọc code không nhầm hai thứ với nhau
from app.models import BookingService as BookingServiceLine
from app.schemas.payment import (FolioLine, FolioOut, InvoiceOut,
                                 InvoiceSummaryOut)
from app.schemas.common import DEFAULT_PAGE_LIMIT

CENT = Decimal("0.01")          # làm tròn tiền tới đồng lẻ thứ 2, như cột Numeric(18, 2)

# Đã hủy / không đến thì không phát sinh tiền (R10: không có cọc) → không thu thêm
UNPAYABLE_STATUSES = (BookingStatus.CANCELLED, BookingStatus.NO_SHOW)


def _money(value: Decimal) -> Decimal:
    # ROUND_HALF_UP: 0.5 làm tròn lên như kế toán; round() của Python làm tròn
    # kiểu "ngân hàng" (0.5 → số chẵn gần nhất) nên không dùng
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _vnd(value: Decimal) -> str:
    """135999.99 → "135.999,99" (dấu chấm ngăn nghìn, phẩy thập phân như ở VN)."""
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


class FolioService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------- FOLIO
    def build(self, booking_id: int) -> FolioOut:
        """Bảng kê tiền của booking, tính lại mỗi lần xem."""
        return self._build(self._load_full(booking_id))

    def _build(self, booking: Booking) -> FolioOut:
        lines: list[FolioLine] = []
        for detail in booking.details:
            room = detail.room
            for rate in detail.night_rates:       # mỗi đêm một dòng
                lines.append(FolioLine(
                    type="room", date=rate.date, quantity=1,
                    description=f"Phòng {room.room_number} ({room.room_type.name}) "
                                f"- đêm {rate.date:%d/%m/%Y}",
                    unit_price=rate.price, amount=rate.price))
        for svc in booking.services:
            lines.append(FolioLine(
                type="service", date=svc.used_date, quantity=svc.quantity,
                description=f"{svc.service.name} ({svc.service.unit})",
                unit_price=svc.unit_price, amount=svc.amount))
        lines.sort(key=lambda x: (x.date, x.type))

        room_charge = sum((x.amount for x in lines if x.type == "room"), Decimal("0"))
        service_charge = sum((x.amount for x in lines if x.type == "service"),
                             Decimal("0"))
        subtotal = room_charge + service_charge
        # Đã xuất hóa đơn → dùng thuế suất ghi trên hóa đơn, không dùng cấu hình
        # hiện tại: năm sau đổi VAT thì folio của booking cũ không bị đổi số
        vat_rate = (booking.invoice.vat_rate if booking.invoice
                    else Decimal(str(settings.VAT_RATE)))   # str(): tránh sai số float
        vat_amount = _money(subtotal * vat_rate)
        total = subtotal + vat_amount
        paid = sum((p.amount for p in booking.payments), Decimal("0"))

        return FolioOut(
            booking_id=booking.id, booking_code=booking.code, status=booking.status,
            customer_name=booking.customer.full_name,
            customer_phone=booking.customer.phone,
            check_in=booking.check_in, check_out=booking.check_out,
            nights=booking.nights, lines=lines,
            room_charge=room_charge, service_charge=service_charge, subtotal=subtotal,
            vat_rate=vat_rate, vat_amount=vat_amount, total=total,
            paid=paid, balance_due=total - paid)

    # ------------------------------------------------------- THANH TOÁN
    def list_payments(self, booking_id: int) -> list[Payment]:
        self._get_booking(booking_id)
        return list(self.db.scalars(
            select(Payment).where(Payment.booking_id == booking_id)
            .order_by(Payment.paid_at, Payment.id)).all())

    def add_payment(self, booking_id: int, dto) -> Payment:
        """Ghi sổ một lần khách trả tiền (tiền mặt/thẻ/chuyển khoản làm bên ngoài).

        Không cho ghi vượt số còn nợ: ghi dư rồi lại phải hoàn, dễ sai sổ.
        Trả sau check-out vẫn được — khách có thể chuyển khoản sau khi đi.
        """
        try:
            lock_booking(self.db, booking_id)    # hai người cùng ghi → không vượt nợ
            booking = self._load_full(booking_id)
            if booking.status in UNPAYABLE_STATUSES:
                raise BusinessError(
                    f"Booking đang {BookingStatus(booking.status).value}, "
                    "không phát sinh tiền để thu", code="BOOKING_NOT_PAYABLE")

            balance_due = self._build(booking).balance_due
            if dto.amount > balance_due:
                raise BusinessError(
                    f"Số tiền {_vnd(dto.amount)} vượt số còn phải trả "
                    f"{_vnd(max(balance_due, Decimal('0')))}",
                    code="AMOUNT_EXCEEDS_BALANCE")

            payment = Payment(booking_id=booking.id, amount=dto.amount,
                              method=dto.method, note=dto.note)
            self.db.add(payment)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(payment)
        return payment

    def refund(self, payment_id: int, dto) -> Payment:
        """Hoàn tiền = thêm một Payment SỐ ÂM. Không sửa/xóa phiếu thu cũ.

        Bảng payments không có cột nối phiếu hoàn với phiếu thu gốc, nên chặn
        bằng hai giới hạn: không quá số của phiếu thu đó, và không quá tổng
        khách đã trả cho booking (để "đã thanh toán" không bao giờ âm).
        """
        original = self.db.get(Payment, payment_id)
        if not original:
            raise NotFoundError("Payment", payment_id)
        try:
            lock_booking(self.db, original.booking_id)
            if original.amount <= 0:
                raise BusinessError("Đây là phiếu hoàn tiền, không hoàn tiếp được",
                                    code="NOT_A_RECEIPT")
            paid = self.db.scalar(select(func.coalesce(func.sum(Payment.amount), 0))
                                  .where(Payment.booking_id == original.booking_id))
            limit = min(original.amount, Decimal(paid))
            if dto.amount > limit:
                raise BusinessError(
                    f"Chỉ hoàn được tối đa {_vnd(limit)}", code="REFUND_EXCEEDS_PAID")

            refund = Payment(
                booking_id=original.booking_id, amount=-dto.amount,
                method=original.method,          # hoàn theo đúng hình thức đã thu
                note=f"Hoàn tiền phiếu thu #{original.id}: {dto.reason}")
            self.db.add(refund)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(refund)
        return refund

    # ------------------------------------------------------- HÓA ĐƠN
    def issue_invoice(self, booking: Booking) -> Invoice:
        """Xuất hóa đơn cho booking. CHƯA commit — check_out() commit chung.

        Đã có hóa đơn thì trả lại cái cũ (cột booking_id UNIQUE: mỗi booking
        một hóa đơn). Lưu cả vat_rate: đổi thuế sau này hóa đơn cũ không đổi.
        """
        existing = self.db.scalar(select(Invoice).where(Invoice.booking_id == booking.id))
        if existing:
            return existing
        folio = self._build(self._load_full(booking.id))
        invoice = Invoice(
            code=self._new_invoice_code(), booking_id=booking.id,
            room_charge=folio.room_charge, service_charge=folio.service_charge,
            subtotal=folio.subtotal, vat_rate=folio.vat_rate,
            vat_amount=folio.vat_amount, total=folio.total)
        self.db.add(invoice)
        self.db.flush()
        return invoice

    def get_invoice(self, invoice_id: int) -> InvoiceOut:
        """Hóa đơn để in: số tiền đọc từ bản ghi invoice (đã chốt), bảng kê và
        số đã trả lấy từ folio hiện tại."""
        invoice = self.db.get(Invoice, invoice_id)
        if not invoice:
            raise NotFoundError("Invoice", invoice_id)
        folio = self._build(self._load_full(invoice.booking_id, include_deleted=True))
        return InvoiceOut(
            **folio.model_dump(exclude={"room_charge", "service_charge", "subtotal",
                                        "vat_rate", "vat_amount", "total",
                                        "balance_due"}),
            id=invoice.id, code=invoice.code, issued_at=invoice.issued_at,
            room_charge=invoice.room_charge, service_charge=invoice.service_charge,
            subtotal=invoice.subtotal, vat_rate=invoice.vat_rate,
            vat_amount=invoice.vat_amount, total=invoice.total,
            balance_due=invoice.total - folio.paid)

    def list_invoices(self, *, from_date: dt.date | None = None,
                      to_date: dt.date | None = None, page: int = 1,
                      limit: int = DEFAULT_PAGE_LIMIT
                      ) -> tuple[list[InvoiceSummaryOut], int]:
        """Hóa đơn xuất trong [from_date, to_date] — tính CẢ ngày to_date."""
        conditions = []
        if from_date is not None:
            conditions.append(Invoice.issued_at >= from_date)
        if to_date is not None:
            # issued_at là datetime: "< ngày hôm sau" để lấy trọn ngày to_date
            conditions.append(Invoice.issued_at < to_date + dt.timedelta(days=1))

        total = self.db.scalar(select(func.count(Invoice.id)).where(*conditions))
        stmt = (select(Invoice).where(*conditions)
                .options(selectinload(Invoice.booking).selectinload(Booking.customer))
                .order_by(Invoice.issued_at.desc(), Invoice.id.desc())
                .offset((page - 1) * limit).limit(limit))
        rows = [InvoiceSummaryOut(
                    id=inv.id, code=inv.code, issued_at=inv.issued_at,
                    booking_id=inv.booking_id, booking_code=inv.booking.code,
                    customer_name=inv.booking.customer.full_name, total=inv.total)
                for inv in self.db.scalars(stmt).all()]
        return rows, total

    def _new_invoice_code(self) -> str:
        """Mã hóa đơn dạng INV261128-A1B2C3, cùng kiểu mã booking."""
        while True:
            code = f"INV{dt.date.today():%y%m%d}-{secrets.token_hex(3).upper()}"
            if not self.db.scalar(select(Invoice.id).where(Invoice.code == code)):
                return code

    def _load_full(self, booking_id: int, include_deleted: bool = False) -> Booking:
        """Nạp booking kèm mọi thứ folio cần, gom bằng selectinload (tránh N+1)."""
        stmt = (select(Booking).where(Booking.id == booking_id)
                .options(
                    selectinload(Booking.customer),
                    selectinload(Booking.details).selectinload(BookingDetail.room)
                    .selectinload(Room.room_type),
                    selectinload(Booking.details).selectinload(BookingDetail.night_rates),
                    selectinload(Booking.services).selectinload(BookingServiceLine.service),
                    selectinload(Booking.payments),
                    selectinload(Booking.invoice))
                .execution_options(populate_existing=True))
        if not include_deleted:
            stmt = stmt.where(Booking.deleted_at.is_(None))
        booking = self.db.scalar(stmt)
        if not booking:
            raise NotFoundError("Booking", booking_id)
        return booking

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
