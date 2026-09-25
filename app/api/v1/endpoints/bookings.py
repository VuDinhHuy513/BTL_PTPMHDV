"""TODO — endpoint booking. Nhóm nhiều endpoint nhất, làm sau availability.

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
from fastapi import APIRouter

router = APIRouter(prefix="/bookings", tags=["06. Đặt phòng"])
