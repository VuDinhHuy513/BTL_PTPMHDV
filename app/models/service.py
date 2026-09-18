"""TODO — Service và BookingService. Xem R9.

┌─ Service — danh mục dịch vụ ──────────────────────────────────────────┐
│ id, name (unique), unit ("lần"/"kg"/"suất"), unit_price               │
└───────────────────────────────────────────────────────────────────────┘

┌─ BookingService — một lần khách dùng dịch vụ ─────────────────────────┐
│ id, booking_id (FK, index), service_id (FK)                          │
│ quantity, used_date, note                                            │
│ unit_price  ← CHỐT giá lúc dùng, không join sang services khi in bill │
└───────────────────────────────────────────────────────────────────────┘
"""
