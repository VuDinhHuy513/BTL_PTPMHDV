"""Danh mục dịch vụ (ăn sáng, giặt ủi...). Admin quản lý. Xem R9.

Sửa giá ở đây KHÔNG làm đổi tiền các dòng dịch vụ đã ghi nhận: mỗi dòng đã chốt
unit_price riêng lúc ghi (FolioService.add_service).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.models import Service


class ServiceCatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Service]:
        return list(self.db.scalars(select(Service).order_by(Service.name)).all())

    def get(self, service_id: int) -> Service:
        service = self.db.get(Service, service_id)
        if not service:
            raise NotFoundError("Service", service_id)
        return service

    def create(self, dto) -> Service:
        self._ensure_name_free(dto.name)
        service = Service(**dto.model_dump())
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        return service

    def update(self, service_id: int, dto) -> Service:
        service = self.get(service_id)
        if dto.name != service.name:
            self._ensure_name_free(dto.name)
        for field, value in dto.model_dump().items():
            setattr(service, field, value)
        self.db.commit()
        self.db.refresh(service)
        return service

    def _ensure_name_free(self, name: str) -> None:
        """Cột name có UNIQUE: kiểm tra trước để trả 409 có code rõ ràng thay vì
        để DB ném IntegrityError thành lỗi 500."""
        if self.db.scalar(select(Service.id).where(Service.name == name)) is not None:
            raise BusinessError(f"Dịch vụ '{name}' đã có trong danh mục",
                                code="SERVICE_NAME_EXISTS")
