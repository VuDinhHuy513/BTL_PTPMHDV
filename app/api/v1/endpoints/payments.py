"""Endpoint folio, thanh toán, hóa đơn (nhóm 09). Quyền: Admin + Lễ tân (R9).

Theo booking:
    GET  /bookings/{id}/folio             bảng kê tiền, tính lại mỗi lần xem
    GET  /bookings/{id}/payments
    POST /bookings/{id}/payments          201, ghi sổ một lần khách trả tiền

Độc lập:
    POST /payments/{payment_id}/refund    201, tạo phiếu số ÂM
    GET  /invoices?from=&to=
    GET  /invoices/{invoice_id}           hóa đơn để in

Xuất hóa đơn nằm ở POST /bookings/{id}/check-out (nhóm 07).
"""
import datetime as dt

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.core.deps import require_front_desk
from app.core.response import PageMeta, ok
from app.db.session import get_db
from app.schemas.common import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.schemas.payment import PaymentIn, PaymentOut, RefundIn
from app.services.folio_service import FolioService

TAG = "09. Thanh toán & hóa đơn"
# Không đặt prefix vì gộp hai nhóm URL khác nhau (/payments, /invoices)
router = APIRouter(tags=[TAG])
booking_payments_router = APIRouter(prefix="/bookings", tags=[TAG])


@booking_payments_router.get("/{booking_id}/folio", summary="Bảng kê tiền của booking")
def get_folio(booking_id: int, db: Session = Depends(get_db),
              _=Depends(require_front_desk)):
    return ok(FolioService(db).build(booking_id))


@booking_payments_router.get("/{booking_id}/payments", summary="Các lần thu / hoàn tiền")
def list_payments(booking_id: int, db: Session = Depends(get_db),
                  _=Depends(require_front_desk)):
    return ok([PaymentOut.model_validate(p)
               for p in FolioService(db).list_payments(booking_id)])


@booking_payments_router.post("/{booking_id}/payments", status_code=201,
                              summary="Ghi sổ khách trả tiền (không vượt số còn nợ)")
def add_payment(booking_id: int, dto: PaymentIn, db: Session = Depends(get_db),
                _=Depends(require_front_desk)):
    return ok(PaymentOut.model_validate(FolioService(db).add_payment(booking_id, dto)))


@router.post("/payments/{payment_id}/refund", status_code=201,
             summary="Hoàn tiền (tạo phiếu số âm, không sửa phiếu cũ)")
def refund_payment(payment_id: int, dto: RefundIn, db: Session = Depends(get_db),
                   _=Depends(require_front_desk)):
    return ok(PaymentOut.model_validate(FolioService(db).refund(payment_id, dto)))


@router.get("/invoices", summary="Danh sách hóa đơn theo ngày xuất")
def list_invoices(
        from_date: dt.date | None = Query(default=None, alias="from"),
        to_date: dt.date | None = Query(default=None, alias="to"),
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
        db: Session = Depends(get_db), _=Depends(require_front_desk)):
    # Ở đây to TÍNH CẢ ngày cuối (hóa đơn từ 01 đến 30), nên to == from là hợp lệ
    if from_date and to_date and to_date < from_date:
        raise RequestValidationError([{
            "type": "value_error", "loc": ("query", "to"),
            "msg": "to không được trước from", "input": to_date.isoformat()}])
    rows, total = FolioService(db).list_invoices(
        from_date=from_date, to_date=to_date, page=page, limit=limit)
    return ok(rows, meta=PageMeta(page=page, limit=limit, total=total))


@router.get("/invoices/{invoice_id}", summary="Chi tiết hóa đơn (để in)")
def get_invoice(invoice_id: int, db: Session = Depends(get_db),
                _=Depends(require_front_desk)):
    return ok(FolioService(db).get_invoice(invoice_id))
