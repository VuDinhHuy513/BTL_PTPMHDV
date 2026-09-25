"""TODO — Booking, BookingDetail, BookingNightRate.

Đọc docs/BUSINESS_RULES.md mục R1, R4, R5 trước khi viết.

┌─ Booking ──────────────────────────────────────────────────────────────┐
│ id, code (unique, index), customer_id (FK)                             │
│ check_in: date, check_out: date, guests: int                           │
│ status: BookingStatus                                                  │
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
│ id, booking_id (FK), room_id (FK, NOT NULL)                            │
│                                                                        │
│ Nhân viên chọn ĐÚNG phòng (101, 102…) ngay lúc khách gọi đặt (R5).     │
│ Không có room_type_id: loại phòng suy ra từ room.room_type_id, giữ     │
│ thêm ở đây chỉ tạo dữ liệu thừa dễ lệch nhau.                          │
│                                                                        │
│ relationship: booking, room, night_rates                               │
│ @property room_charge → tổng giá các đêm                               │
└────────────────────────────────────────────────────────────────────────┘

┌─ BookingNightRate — giá CHỐT của từng đêm ────────────────────────────┐
│ id, booking_detail_id (FK), date: date, price: Numeric(18,2)           │
│                                                                        │
│ Vì sao cần bảng này dù giá mỗi đêm giống nhau? Xem docs/CONVENTIONS.md │
│ mục 4: Admin sửa base_price sau này thì booking cũ không được đổi giá. │
│ Đồng thời cho phép đổi phòng giữa kỳ sang loại phòng khác giá.         │
└────────────────────────────────────────────────────────────────────────┘
"""
