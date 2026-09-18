"""TODO — Booking, BookingDetail, BookingNightRate.

Đọc docs/BUSINESS_RULES.md mục R1, R4, R5 trước khi viết.

┌─ Booking ──────────────────────────────────────────────────────────────┐
│ id, code (unique, index), customer_id (FK)                             │
│ check_in: date, check_out: date, guests: int                           │
│ status: BookingStatus, deposit: Numeric(18,2)                          │
│ note, cancel_reason                                                    │
│ created_at, checked_in_at, checked_out_at                              │
│ deleted_at  ← soft delete, KHÔNG xóa cứng (R10)                        │
│                                                                        │
│ relationship: customer, details, services, payments                    │
│ @property nights → (check_out - check_in).days                         │
│                                                                        │
│ __table_args__: Index trên (check_in, check_out, status)               │
│   ↳ đây là query nóng nhất hệ thống, không có index sẽ chậm            │
└────────────────────────────────────────────────────────────────────────┘

┌─ BookingDetail — mỗi dòng là MỘT phòng trong booking ──────────────────┐
│ id, booking_id (FK), room_type_id (FK)                                 │
│ room_id: FK nullable  ← để NULL cho tới lúc check-in (R5)              │
│                                                                        │
│ Vì sao nullable? Lúc đặt khách chỉ chọn LOẠI phòng. Gán phòng cứng     │
│ từ đầu làm lễ tân mất linh hoạt sắp xếp.                               │
│                                                                        │
│ relationship: booking, room_type, room, night_rates                    │
│ @property room_charge → tổng giá các đêm                               │
└────────────────────────────────────────────────────────────────────────┘

┌─ BookingNightRate — giá CHỐT của từng đêm ────────────────────────────┐
│ id, booking_detail_id (FK), date: date, price: Numeric(18,2)           │
│                                                                        │
│ Vì sao cần bảng này? Xem docs/CONVENTIONS.md mục 4.                    │
│ Nếu hóa đơn join sang rate_prices để tính, sửa bảng giá sẽ làm đổi     │
│ số tiền của hóa đơn đã xuất từ trước.                                  │
└────────────────────────────────────────────────────────────────────────┘
"""
