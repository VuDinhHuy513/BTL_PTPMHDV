"""Endpoint khách hàng. Quyền: tất cả dùng require_front_desk (Admin + Lễ tân).

    GET  /customers?search=&page=&limit=    tìm theo tên/sđt/email, có PageMeta
    GET  /customers/{id}
    GET  /customers/{id}/bookings           lịch sử đặt phòng, có PageMeta
    POST /customers                         201
    PUT  /customers/{id}

Khách cũng được TỰ TẠO khi đặt phòng với số điện thoại mới (R5); các endpoint
này để tìm khách cũ, sửa thông tin sai và xem lịch sử.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_front_desk
from app.core.response import PageMeta, ok
from app.db.session import get_db
from app.schemas.booking import BookingOut
from app.schemas.common import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.schemas.customer import CustomerIn, CustomerOut
from app.services.booking_service import BookingService
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["05. Khách hàng"])

# Giới hạn độ dài chuỗi tìm kiếm: dài hơn cả họ tên tối đa thì chắc chắn sai
MAX_SEARCH_LENGTH = 100


@router.get("", summary="Danh sách / tìm kiếm khách hàng")
def list_customers(
        search: str | None = Query(default=None, max_length=MAX_SEARCH_LENGTH,
                                   description="Tên, số điện thoại hoặc email"),
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
        db: Session = Depends(get_db), _=Depends(require_front_desk)):
    # strip: "?search=   " coi như không tìm, tránh lọc theo chuỗi toàn dấu cách
    customers, total = CustomerService(db).list(
        search=(search or "").strip() or None, page=page, limit=limit)
    return ok([CustomerOut.model_validate(c) for c in customers],
              meta=PageMeta(page=page, limit=limit, total=total))


@router.get("/{customer_id}", summary="Chi tiết khách hàng")
def get_customer(customer_id: int, db: Session = Depends(get_db),
                 _=Depends(require_front_desk)):
    return ok(CustomerOut.model_validate(CustomerService(db).get(customer_id)))


@router.get("/{customer_id}/bookings", summary="Lịch sử đặt phòng của khách")
def list_customer_bookings(
        customer_id: int,
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
        db: Session = Depends(get_db), _=Depends(require_front_desk)):
    # Kiểm tra khách tồn tại trước: khách không có thì 404, không phải danh sách rỗng
    CustomerService(db).get(customer_id)
    bookings, total = BookingService(db).list(
        customer_id=customer_id, page=page, limit=limit)
    return ok([BookingOut.model_validate(b) for b in bookings],
              meta=PageMeta(page=page, limit=limit, total=total))


@router.post("", status_code=201, summary="Thêm khách hàng")
def create_customer(dto: CustomerIn, db: Session = Depends(get_db),
                    _=Depends(require_front_desk)):
    return ok(CustomerOut.model_validate(CustomerService(db).create(dto)))


@router.put("/{customer_id}", summary="Sửa thông tin khách hàng")
def update_customer(customer_id: int, dto: CustomerIn, db: Session = Depends(get_db),
                    _=Depends(require_front_desk)):
    return ok(CustomerOut.model_validate(CustomerService(db).update(customer_id, dto)))
