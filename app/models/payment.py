"""TODO — Payment và Invoice. Xem R9.

┌─ Payment ─────────────────────────────────────────────────────────────┐
│ id, booking_id (FK, index)                                            │
│ amount: Numeric(18,2)   ← số ÂM nghĩa là hoàn tiền                    │
│ method: PaymentMethod, note, paid_at                                  │
└───────────────────────────────────────────────────────────────────────┘

┌─ Invoice ─────────────────────────────────────────────────────────────┐
│ id, code (unique, index), booking_id (FK, index)                      │
│ room_charge, service_charge, subtotal                                 │
│ vat_rate: Numeric(5,4), vat_amount, total                             │
│ issued_at                                                             │
│                                                                       │
│ Lưu cả vat_rate vào hóa đơn: năm sau nhà nước đổi thuế suất thì hóa   │
│ đơn cũ vẫn phải giữ nguyên con số đã xuất.                            │
└───────────────────────────────────────────────────────────────────────┘
"""
