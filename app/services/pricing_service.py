"""Tính giá phòng theo từng đêm. Xem docs/BUSINESS_RULES.md mục R1, R2.

Test tương ứng: tests/test_pricing.py  (chạy `pytest tests/test_pricing.py`)
"""
import datetime as dt
from decimal import Decimal

from sqlalchemy.orm import Session


class PricingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_nightly_rates(
        self, room_type_id: int, check_in: dt.date, check_out: dt.date
    ) -> list[tuple[dt.date, Decimal]]:
        """Trả về [(ngày, giá)] cho khoảng [check_in, check_out).

        TODO — các bước:
          1. Lấy base_price của room_type. Không có → raise NotFoundError.
          2. Nạp mọi RatePrice trong khoảng, gom thành dict {date: price}.
             Điều kiện: date >= check_in AND date < check_out
          3. Lặp từ check_in, dừng khi d >= check_out:
                 giá = overrides.get(d, base_price)

        ⚠ BẪY SỐ MỘT: dùng `while d < check_out`, KHÔNG phải `<=`.
          Ở 01/10 → 05/10 là 4 đêm (01,02,03,04), không phải 5.
          Đêm của ngày trả phòng không tính tiền.

        ⚠ BẪY SỐ HAI: đừng làm `số_đêm × base_price`. Khách ở vắt qua cuối
          tuần sẽ đi qua nhiều mức giá khác nhau.
        """
        raise NotImplementedError("TODO: xem docstring ở trên")

    def total_for(self, room_type_id: int, check_in: dt.date,
                  check_out: dt.date) -> Decimal:
        """Tổng tiền phòng. TODO: cộng dồn kết quả của get_nightly_rates."""
        raise NotImplementedError("TODO")
