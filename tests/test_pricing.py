"""Test PricingService — chỗ sinh viên hay sai nhất là đếm số đêm."""
import datetime as dt
from decimal import Decimal

from tests.helpers import require_models

require_models("RatePrice", "RoomType")

from app.models import RatePrice, RoomType
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


def test_gia_mac_dinh_lay_base_price(db):
    std = _std(db)
    rates = PricingService(db).get_nightly_rates(
        std.id, dt.date(2026, 10, 1), dt.date(2026, 10, 4))
    assert all(p == Decimal("500000") for _, p in rates)


def test_gia_override_theo_ngay(db):
    """Khách ở vắt qua nhiều mức giá — phải tính từng đêm, không nhân số đêm."""
    std = _std(db)
    db.add_all([
        RatePrice(room_type_id=std.id, date=dt.date(2026, 10, 2),
                  price=Decimal("650000")),
        RatePrice(room_type_id=std.id, date=dt.date(2026, 10, 3),
                  price=Decimal("650000")),
    ])
    db.commit()

    svc = PricingService(db)
    rates = svc.get_nightly_rates(std.id, dt.date(2026, 10, 1), dt.date(2026, 10, 5))

    assert [p for _, p in rates] == [
        Decimal("500000"), Decimal("650000"), Decimal("650000"), Decimal("500000")]
    # Nếu tính sai kiểu 4 × 500000 = 2.000.000 thì test này fail
    assert svc.total_for(std.id, dt.date(2026, 10, 1),
                         dt.date(2026, 10, 5)) == Decimal("2300000")


def test_override_ngoai_khoang_khong_anh_huong(db):
    """Giá của ngày trả phòng không được tính vào hóa đơn."""
    std = _std(db)
    db.add(RatePrice(room_type_id=std.id, date=dt.date(2026, 10, 5),
                     price=Decimal("9999000")))
    db.commit()

    total = PricingService(db).total_for(
        std.id, dt.date(2026, 10, 1), dt.date(2026, 10, 5))
    assert total == Decimal("2000000")     # 4 đêm × 500k, không dính 9.999.000
