"""TODO — RatePrice: giá override cho (loại phòng, ngày). Xem R2.

    id, room_type_id (FK, index), date: Date (index), price: Numeric(18,2)
    UniqueConstraint("room_type_id", "date")   ← một ngày chỉ một giá

Ngày nào không có bản ghi ở đây thì lấy RoomType.base_price.
"""
