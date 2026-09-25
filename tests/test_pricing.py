"""Test PricingService — chỗ sinh viên hay sai nhất là đếm số đêm."""
import datetime as dt
from decimal import Decimal

from tests.helpers import require_models

require_models("RoomType")

from app.models import RoomType
from app.services.pricing_service import PricingService


def _std(db) -> RoomType:
    return db.query(RoomType).filter_by(name="Standard").one()


def test_so_dem_khong_tinh_dem_tra_phong(db):
    """Ở từ 01/10 đến 05/10 là 4 đêm, KHÔNG phải 5."""
    std = _std(db)
    rates = PricingService(db).get_nightly_rates(
        std.id, dt.date(2026, 10, 1), dt.date(2026, 10, 5))

    assert len(rates) == 4
    assert rates[0][0] == dt.date(2026, 10, 1)
    assert rates[-1][0] == dt.date(2026, 10, 4)      # không có ngày 05


def test_mot_dem(db):
    std = _std(db)
    rates = PricingService(db).get_nightly_rates(
        std.id, dt.date(2026, 10, 1), dt.date(2026, 10, 2))
    assert len(rates) == 1


def test_gia_moi_dem_la_base_price(db):
    std = _std(db)
    rates = PricingService(db).get_nightly_rates(
        std.id, dt.date(2026, 10, 1), dt.date(2026, 10, 4))
    assert all(p == Decimal("500000") for _, p in rates)


def test_tong_tien_bang_so_dem_nhan_base_price(db):
    """Giá cố định theo loại phòng: 4 đêm × 500k = 2.000.000."""
    std = _std(db)
    total = PricingService(db).total_for(
        std.id, dt.date(2026, 10, 1), dt.date(2026, 10, 5))
    assert total == Decimal("2000000")
