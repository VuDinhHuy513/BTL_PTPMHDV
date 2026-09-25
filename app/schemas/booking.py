"""TODO — DTO cho booking.

BookingCreateIn    customer_id HOẶC customer (CustomerIn: full_name, phone…)
                   check_in, check_out, guests, room_ids[], note
                   @model_validator kiểm tra:
                     - check_out > check_in
                     - check_in >= hôm nay
                     - số đêm <= MAX_NIGHTS_PER_BOOKING
                     - có customer_id hoặc customer
                     - room_ids không rỗng và không trùng nhau (422)
                   Việc cần DB thì để Service: phòng còn trống, guests <= tổng
                   sức chứa các phòng đã chọn.

BookingUpdateIn    check_in, check_out, guests, note
CancelIn           reason (min_length=1)
CheckInIn          id_card_number (không bắt buộc)
WalkInIn           customer, check_out, guests, room_ids[], note
                   (không có check_in: khách vãng lai luôn nhận phòng hôm nay)
ChangeRoomIn       booking_detail_id, new_room_id, reason

BookingDetailOut   id, room_id, room_number, room_type_id, night_rates[]
BookingOut         id, code, customer, check_in, check_out, nights, guests,
                   status, details[], room_charge

Xem docs/CONVENTIONS.md mục 9 để biết cái gì validate ở Pydantic,
cái gì validate ở Service.
"""
