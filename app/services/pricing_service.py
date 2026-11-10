"""Tính giá phòng theo từng đêm. Xem docs/BUSINESS_RULES.md mục R1, R2.

Test tương ứng: tests/test_pricing.py  (chạy `pytest tests/test_pricing.py`)
"""
import datetime as dt
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import RoomType


class PricingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_nightly_rates(
        self, room_type_id: int, check_in: dt.date, check_out: dt.date
    ) -> list[tuple[dt.date, Decimal]]:
        """Trả về [(ngày, giá)] cho khoảng [check_in, check_out).

        Giá cố định theo loại phòng (R2): mọi đêm đều là base_price. Vẫn trả về
        danh sách từng đêm vì booking_night_rates chốt giá theo từng đêm.

        Dùng `while d < check_out`, không phải `<=`: ở 01/10 → 05/10 là 4 đêm
        (01,02,03,04), đêm của ngày trả phòng không tính tiền.
        """
        room_type = self.db.get(RoomType, room_type_id)
        if not room_type:
            raise NotFoundError("RoomType", room_type_id)

        rates: list[tuple[dt.date, Decimal]] = []
        d = check_in
        while d < check_out:
            rates.append((d, room_type.base_price))
            d += dt.timedelta(days=1)
        return rates

    def total_for(self, room_type_id: int, check_in: dt.date,
                  check_out: dt.date) -> Decimal:
        """Tổng tiền của MỘT phòng thuộc loại này."""
        rates = self.get_nightly_rates(room_type_id, check_in, check_out)
        return sum((price for _, price in rates), Decimal("0"))
