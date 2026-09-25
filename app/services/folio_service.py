"""Folio = sổ ghi nợ của booking: tiền phòng + dịch vụ + thuế − đã trả. Xem R9.

TODO — các hàm cần viết:

    build(booking) -> FolioOut
        Duyệt booking.details → cộng night_rates thành room_charge, mỗi đêm
        là một dòng trong folio.
        Duyệt booking_services → service_charge.
        subtotal = room_charge + service_charge
        vat_amount = subtotal * settings.VAT_RATE   ← KHÔNG viết 0.08
        total = subtotal + vat_amount
        paid = tổng payments (số dương là thu, số âm là hoàn)
        balance_due = total - paid

    add_service(booking, service_id, quantity, used_date, note)
        ⚠ Copy unit_price từ Service vào BookingService — CHỐT giá lúc dùng.

    remove_service(booking_id, line_id)

    add_payment(booking, amount, method, note)

    refund(payment_id, amount, reason)
        Tạo Payment với amount ÂM. Không sửa bản ghi cũ.

    issue_invoice(booking) -> Invoice
        Đã có hóa đơn rồi thì trả về cái cũ, không tạo trùng.
        Lưu cả vat_rate vào hóa đơn.
"""
