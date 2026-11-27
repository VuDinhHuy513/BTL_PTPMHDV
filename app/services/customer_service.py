"""Khách hàng: tìm kiếm, xem, thêm, sửa. Xem R5.

Đặt phòng đã TỰ TẠO khách khi số điện thoại chưa có (BookingService._resolve_customer).
Service này lo phần còn lại: tìm khách cũ để lấy customer_id, sửa thông tin sai,
xem hồ sơ. Lịch sử đặt phòng dùng lại BookingService.list(customer_id=...).
"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.models import Customer
from app.schemas.common import DEFAULT_PAGE_LIMIT


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, *, search: str | None = None, page: int = 1,
             limit: int = DEFAULT_PAGE_LIMIT) -> tuple[list[Customer], int]:
        """Tìm theo tên / số điện thoại / email (chứa chuỗi, không phân biệt hoa
        thường). Trả về (danh_sách, tổng_số) để endpoint dựng PageMeta."""
        conditions = []
        if search:
            # autoescape: khách gõ "%" hay "_" thì tìm đúng ký tự đó, không bị
            # SQL hiểu thành ký tự đại diện (LIKE '%%%' khớp mọi dòng)
            conditions.append(or_(
                Customer.full_name.icontains(search, autoescape=True),
                Customer.phone.contains(search, autoescape=True),
                Customer.email.icontains(search, autoescape=True)))

        total = self.db.scalar(select(func.count(Customer.id)).where(*conditions))
        stmt = (select(Customer).where(*conditions)
                .order_by(Customer.created_at.desc(), Customer.id.desc())
                .offset((page - 1) * limit).limit(limit))
        return list(self.db.scalars(stmt).all()), total

    def get(self, customer_id: int) -> Customer:
        customer = self.db.get(Customer, customer_id)
        if not customer:
            raise NotFoundError("Customer", customer_id)
        return customer

    def create(self, dto) -> Customer:
        self._ensure_phone_free(dto.phone)
        customer = Customer(**dto.model_dump())
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def update(self, customer_id: int, dto) -> Customer:
        """PUT: thay toàn bộ thông tin. Bỏ trống email/CCCD... là xóa giá trị cũ."""
        customer = self.get(customer_id)
        if dto.phone != customer.phone:
            self._ensure_phone_free(dto.phone, exclude_id=customer_id)
        for field, value in dto.model_dump().items():
            setattr(customer, field, value)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def _ensure_phone_free(self, phone: str, exclude_id: int | None = None) -> None:
        """Số điện thoại là thứ đặt phòng dùng để nhận ra khách cũ (R5). Hai khách
        trùng số thì lần đặt sau không biết dùng ai → chặn ngay từ đầu."""
        stmt = select(Customer.id).where(Customer.phone == phone)
        if exclude_id is not None:
            stmt = stmt.where(Customer.id != exclude_id)
        if self.db.scalar(stmt.limit(1)) is not None:
            raise BusinessError(f"Số điện thoại {phone} đã thuộc về khách khác",
                                code="PHONE_ALREADY_EXISTS")
