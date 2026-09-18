"""TODO — DTO cho booking.

BookingLineIn      room_type_id, quantity (ge=1, le=10)

BookingCreateIn    customer_id HOẶC customer (CustomerIn)
                   check_in, check_out, guests, lines[], deposit, note
                   @model_validator kiểm tra:
                     - check_out > check_in
                     - check_in >= hôm nay
                     - số đêm <= MAX_NIGHTS_PER_BOOKING
                     - có customer_id hoặc customer

BookingUpdateIn    check_in, check_out, guests, note
CancelIn           reason (min_length=1)
CheckInIn          assignments[], id_card_number, deposit
WalkInIn           customer, check_in, check_out, guests, room_type_id, quantity
ChangeRoomIn       booking_detail_id, new_room_id, reason

BookingDetailOut   id, room_type_id, room_id, room_number, night_rates[]
BookingOut         id, code, customer, check_in, check_out, nights, guests,
                   status, deposit, details[], room_charge

Xem docs/CONVENTIONS.md mục 9 để biết cái gì validate ở Pydantic,
cái gì validate ở Service.
"""
