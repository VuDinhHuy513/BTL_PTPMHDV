"""DTO Pydantic cho request/response.

XEM room.py LÀM MẪU — các schema khác viết theo đúng kiểu đó.

Quy ước đặt tên:
    *In   → dữ liệu client gửi lên   (RoomTypeIn, BookingCreateIn)
    *Out  → dữ liệu trả về client    (RoomTypeOut, BookingOut)

Schema *Out kế thừa ORMBase (common.py) để dùng được model_validate(entity).
"""
