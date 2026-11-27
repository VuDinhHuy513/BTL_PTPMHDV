"""Endpoint dịch vụ (nhóm 08).

Danh mục — sửa danh mục chỉ Admin, xem thì mọi vai trò:
    GET  /services
    POST /services                     201, Admin
    PUT  /services/{service_id}        Admin

Dịch vụ khách dùng trong booking — nhân viên (Admin + Lễ tân):
    GET    /bookings/{id}/services
    POST   /bookings/{id}/services              201, chốt giá lúc ghi
    DELETE /bookings/{id}/services/{line_id}
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_admin, require_any, require_front_desk
from app.core.response import ok
from app.db.session import get_db
from app.schemas.common import MessageOut
from app.schemas.service import (BookingServiceIn, BookingServiceOut, ServiceIn,
                                 ServiceOut)
from app.services.folio_service import FolioService
from app.services.service_catalog_service import ServiceCatalogService

router = APIRouter(prefix="/services", tags=["08. Dịch vụ"])
# Cùng nhóm Swagger 08 nhưng URL nằm dưới /bookings
booking_services_router = APIRouter(prefix="/bookings", tags=["08. Dịch vụ"])


@router.get("", summary="Danh mục dịch vụ")
def list_services(db: Session = Depends(get_db), _=Depends(require_any)):
    return ok([ServiceOut.model_validate(s) for s in ServiceCatalogService(db).list()])


@router.post("", status_code=201, summary="Thêm dịch vụ vào danh mục")
def create_service(dto: ServiceIn, db: Session = Depends(get_db),
                   _=Depends(require_admin)):
    return ok(ServiceOut.model_validate(ServiceCatalogService(db).create(dto)))


@router.put("/{service_id}", summary="Sửa dịch vụ (không ảnh hưởng dòng đã ghi)")
def update_service(service_id: int, dto: ServiceIn, db: Session = Depends(get_db),
                   _=Depends(require_admin)):
    return ok(ServiceOut.model_validate(ServiceCatalogService(db).update(service_id, dto)))


@booking_services_router.get("/{booking_id}/services",
                             summary="Dịch vụ khách đã dùng trong booking")
def list_booking_services(booking_id: int, db: Session = Depends(get_db),
                          _=Depends(require_front_desk)):
    lines = FolioService(db).list_services(booking_id)
    return ok([BookingServiceOut.model_validate(x) for x in lines])


@booking_services_router.post("/{booking_id}/services", status_code=201,
                              summary="Ghi nhận khách dùng dịch vụ (chỉ khi CheckedIn)")
def add_booking_service(booking_id: int, dto: BookingServiceIn,
                        db: Session = Depends(get_db), _=Depends(require_front_desk)):
    line = FolioService(db).add_service(booking_id, dto)
    return ok(BookingServiceOut.model_validate(line))


@booking_services_router.delete("/{booking_id}/services/{line_id}",
                                summary="Xóa dòng dịch vụ ghi nhầm (chỉ khi CheckedIn)")
def remove_booking_service(booking_id: int, line_id: int, db: Session = Depends(get_db),
                           _=Depends(require_front_desk)):
    FolioService(db).remove_service(booking_id, line_id)
    return ok(MessageOut(message="Đã xóa dòng dịch vụ"))
