"""Endpoint booking. Nhóm nhiều endpoint nhất.

Đã làm: GET /bookings, POST /bookings, GET /bookings/{id}, GET /bookings/code/{code},
        PUT/DELETE /bookings/{id}, POST /bookings/{id}/cancel, POST /bookings/{id}/no-show,
        POST /bookings/walk-in, POST /bookings/{id}/check-in, POST /bookings/{id}/change-room,
        POST /bookings/{id}/check-out.
Dịch vụ, folio, thanh toán: xem services.py và payments.py.
Còn lại: xem danh sách bên dưới.

Quyền: tất cả dùng require_front_desk (Admin + Lễ tân).

ĐỌC DỮ LIỆU
    GET    /bookings                    lọc status/from/to/customer_id + phân trang
    GET    /bookings/{id}
    GET    /bookings/code/{code}

GHI DỮ LIỆU
    POST   /bookings                    201, body có room_ids[] (chọn đúng phòng)
    PUT    /bookings/{id}               sửa ngày ở / số khách / ghi chú
    DELETE /bookings/{id}               xóa mềm

CHUYỂN TRẠNG THÁI — dùng POST /{id}/{hành-động}, KHÔNG dùng PUT sửa status.
Lý do: xem docs/CONVENTIONS.md mục 7.
    POST   /bookings/walk-in            201, khách vãng lai (tạo + check-in)
    POST   /bookings/{id}/cancel        body: reason
    POST   /bookings/{id}/no-show       chỉ từ ngày nhận phòng trở đi
    POST   /bookings/{id}/check-in
    POST   /bookings/{id}/change-room   Confirmed hoặc CheckedIn
    POST   /bookings/{id}/check-out     trả về InvoiceOut

DỊCH VỤ & THANH TOÁN
    GET    /bookings/{id}/folio
    GET    /bookings/{id}/services
    POST   /bookings/{id}/services      201
    DELETE /bookings/{id}/services/{line_id}
    GET    /bookings/{id}/payments
    POST   /bookings/{id}/payments      201

⚠ Thứ tự khai báo route quan trọng: /bookings/walk-in và /bookings/code/{code}
  phải đặt TRƯỚC /bookings/{id}, nếu không FastAPI khớp "walk-in" vào {id}
  rồi báo lỗi không parse được thành int.
"""
import datetime as dt

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.core.deps import require_front_desk
from app.core.response import PageMeta, ok
from app.db.session import get_db
from app.models import BookingSource, BookingStatus
from app.schemas.booking import (BookingCreateIn, BookingOut, BookingUpdateIn,
                                 CancelIn, ChangeRoomIn, CheckInIn, WalkInIn)
from app.schemas.common import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, MessageOut
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["06. Đặt phòng"])
# Cùng prefix /bookings nhưng tách router để Swagger hiện thành nhóm 07 riêng như
# API_SPEC (tags khai báo ở router; gắn tag ở từng route thì route hiện ở CẢ hai nhóm)
stay_router = APIRouter(prefix="/bookings", tags=["07. Nhận / trả phòng"])


@router.get("", summary="Danh sách booking (lọc + phân trang)")
def list_bookings(
        status: BookingStatus | None = Query(default=None),
        # "from" là từ khóa Python nên tên biến là from_date, alias giữ URL là ?from=
        from_date: dt.date | None = Query(default=None, alias="from"),
        to_date: dt.date | None = Query(default=None, alias="to"),
        customer_id: int | None = Query(default=None, ge=1),
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
        db: Session = Depends(get_db), _=Depends(require_front_desk)):
    # Kiểm tra quan hệ giữa 2 tham số → lỗi đầu vào (422), không phải lỗi nghiệp vụ
    if from_date and to_date and to_date <= from_date:
        raise RequestValidationError([{
            "type": "value_error", "loc": ("query", "to"),
            "msg": "to phải sau from", "input": to_date.isoformat()}])

    bookings, total = BookingService(db).list(
        status=status, from_date=from_date, to_date=to_date,
        customer_id=customer_id, page=page, limit=limit)
    return ok([BookingOut.model_validate(b) for b in bookings],
              meta=PageMeta(page=page, limit=limit, total=total))


@router.post("", status_code=201, summary="Nhân viên đặt phòng")
def create_booking(dto: BookingCreateIn, db: Session = Depends(get_db),
                   _=Depends(require_front_desk)):
    booking = BookingService(db).create(dto, source=BookingSource.STAFF)
    return ok(BookingOut.model_validate(booking))


# /code/{code} khai báo TRƯỚC /{booking_id}, nếu không "code" bị khớp vào {booking_id}
@router.get("/code/{code}", summary="Tra booking theo mã")
def get_booking_by_code(code: str, db: Session = Depends(get_db),
                        _=Depends(require_front_desk)):
    return ok(BookingOut.model_validate(BookingService(db).get_by_code(code)))


@router.get("/{booking_id}", summary="Chi tiết booking")
def get_booking(booking_id: int, db: Session = Depends(get_db),
                _=Depends(require_front_desk)):
    return ok(BookingOut.model_validate(BookingService(db).get(booking_id)))


@router.put("/{booking_id}", summary="Sửa ngày ở / số khách / ghi chú (chỉ khi Confirmed)")
def update_booking(booking_id: int, dto: BookingUpdateIn, db: Session = Depends(get_db),
                   _=Depends(require_front_desk)):
    return ok(BookingOut.model_validate(BookingService(db).update(booking_id, dto)))


@router.delete("/{booking_id}", summary="Xóa mềm booking")
def delete_booking(booking_id: int, db: Session = Depends(get_db),
                   _=Depends(require_front_desk)):
    BookingService(db).soft_delete(booking_id)
    return ok(MessageOut(message="Đã xóa booking"))


# Chuyển trạng thái dùng POST /{id}/{hành-động}, không PUT sửa status (CONVENTIONS mục 7)
@router.post("/{booking_id}/cancel", summary="Hủy booking (chỉ khi Confirmed)")
def cancel_booking(booking_id: int, dto: CancelIn, db: Session = Depends(get_db),
                   _=Depends(require_front_desk)):
    booking = BookingService(db).cancel(booking_id, dto.reason)
    return ok(BookingOut.model_validate(booking))


@router.post("/{booking_id}/no-show", summary="Đánh dấu khách không đến")
def no_show_booking(booking_id: int, db: Session = Depends(get_db),
                    _=Depends(require_front_desk)):
    return ok(BookingOut.model_validate(BookingService(db).no_show(booking_id)))


# ---------------------------------------------------------- 07. Nhận / trả phòng
# walk-in là đường dẫn cố định: router này được include SAU router chính, nhưng
# không đụng /{booking_id} vì router chính không có POST /{booking_id}.
@stay_router.post("/walk-in", status_code=201, summary="Khách vãng lai: đặt + nhận phòng ngay")
def walk_in(dto: WalkInIn, db: Session = Depends(get_db), _=Depends(require_front_desk)):
    return ok(BookingOut.model_validate(BookingService(db).walk_in(dto)))


@stay_router.post("/{booking_id}/check-in", summary="Nhận phòng")
def check_in(booking_id: int, dto: CheckInIn, db: Session = Depends(get_db),
             _=Depends(require_front_desk)):
    booking = BookingService(db).check_in(booking_id, dto.id_card_number)
    return ok(BookingOut.model_validate(booking))


@stay_router.post("/{booking_id}/change-room",
                  summary="Đổi phòng (Confirmed hoặc CheckedIn)")
def change_room(booking_id: int, dto: ChangeRoomIn, db: Session = Depends(get_db),
                _=Depends(require_front_desk)):
    booking = BookingService(db).change_room(
        booking_id, dto.booking_detail_id, dto.new_room_id, dto.reason)
    return ok(BookingOut.model_validate(booking))


@stay_router.post("/{booking_id}/check-out",
                  summary="Trả phòng + xuất hóa đơn (không bắt trả đủ tiền)")
def check_out(booking_id: int, db: Session = Depends(get_db),
              _=Depends(require_front_desk)):
    return ok(BookingService(db).check_out(booking_id))
