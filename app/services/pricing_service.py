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

        Giá cố định theo loại phòng (R2): mọi đêm đều là base_price. Vẫn trả về
        danh sách từng đêm vì booking_night_rates chốt giá theo từng đêm.

        TODO — các bước:
          1. Lấy base_price của room_type. Không có → raise NotFoundError.
          2. Lặp từ check_in, dừng khi d >= check_out, mỗi đêm một cặp
             (d, base_price).

        ⚠ BẪY: dùng `while d < check_out`, KHÔNG phải `<=`.
          Ở 01/10 → 05/10 là 4 đêm (01,02,03,04), không phải 5.
          Đêm của ngày trả phòng không tính tiền.
        """
        raise NotImplementedError("TODO: xem docstring ở trên")

    def total_for(self, room_type_id: int, check_in: dt.date,
                  check_out: dt.date) -> Decimal:
        """Tổng tiền của MỘT phòng thuộc loại này. TODO: cộng dồn get_nightly_rates."""
        raise NotImplementedError("TODO")
