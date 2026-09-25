"""Test AvailabilityService — tập trung vào các case biên hay sai.

Nhân viên chọn đúng phòng lúc đặt, nên booking trong test giữ phòng cụ thể.
"""
import datetime as dt
import itertools
from decimal import Decimal

from tests.helpers import require_models

require_models("Booking", "BookingDetail", "BookingNightRate", "BookingStatus",
               "Customer", "Room", "RoomType")

from app.models import (Booking, BookingDetail, BookingNightRate, BookingStatus,
                        Customer, Room, RoomType)
from app.services.availability_service import AvailabilityService

D = dt.date
_seq = itertools.count(1)


def _mk_booking(db, rooms, ci: D, co: D, status=BookingStatus.CONFIRMED) -> Booking:
    """Tạo booking giữ các phòng `rooms` (danh sách Room) trong [ci, co)."""
    c = db.query(Customer).first()
    if not c:
        c = Customer(full_name="Khách test", phone="0900000000")
        db.add(c)
        db.flush()
    b = Booking(code=f"BK-TEST-{next(_seq)}", customer_id=c.id,
                check_in=ci, check_out=co, guests=1, status=status)
    for room in rooms:
        b.details.append(BookingDetail(
            room_id=room.id,
            night_rates=[BookingNightRate(date=ci, price=Decimal("500000"))]))
    db.add(b)
    db.commit()
    return b


def _std(db):
    return db.query(RoomType).filter_by(name="Standard").one()


def _std_rooms(db) -> list[Room]:
    """Các phòng Standard: 101, 102, 103."""
    return (db.query(Room).filter_by(room_type_id=_std(db).id)
            .order_by(Room.room_number).all())


def test_loai_tru_phong_bao_tri(db):
    """Deluxe có 2 phòng nhưng 1 phòng OutOfOrder → chỉ còn 1."""
    res = AvailabilityService(db).search(D(2026, 10, 1), D(2026, 10, 5), guests=1)
    deluxe = next(r for r in res.room_types if r.name == "Deluxe")
    assert deluxe.available_count == 1
    assert [r.room_number for r in deluxe.rooms] == ["201"]


def test_loc_theo_suc_chua(db):
    """4 khách thì Standard (sức chứa 2) không được trả về."""
    res = AvailabilityService(db).search(D(2026, 10, 1), D(2026, 10, 5), guests=4)
    assert [r.name for r in res.room_types] == ["Deluxe"]


def test_booking_giao_nhau_thi_chiem_phong(db):
    std = _std(db)
    _mk_booking(db, _std_rooms(db)[:1], D(2026, 10, 3), D(2026, 10, 7))

    svc = AvailabilityService(db)
    # tra 01→05 giao với 03→07 → mất 1 phòng
    assert svc.count_available(std.id, D(2026, 10, 1), D(2026, 10, 5)) == 2


def test_case_bien_tra_phong_va_nhan_phong_cung_ngay(db):
    """Khách A trả phòng ngày 05, khách B nhận phòng ngày 05 → KHÔNG trùng.

    Đây là lý do dùng < và > chứ không phải <= và >=.
    """
    std = _std(db)
    _mk_booking(db, _std_rooms(db)[:1], D(2026, 10, 1), D(2026, 10, 5))

    svc = AvailabilityService(db)
    # nhận phòng đúng ngày khách cũ trả → vẫn còn đủ 3 phòng
    assert svc.count_available(std.id, D(2026, 10, 5), D(2026, 10, 8)) == 3
    # và ngược lại: trả phòng đúng ngày khách cũ nhận
    assert svc.count_available(std.id, D(2026, 9, 28), D(2026, 10, 1)) == 3


def test_trang_thai_khong_chan_phong(db):
    """Cancelled / NoShow / CheckedOut KHÔNG chiếm phòng."""
    std = _std(db)
    room = _std_rooms(db)[:1]
    for st in (BookingStatus.CANCELLED, BookingStatus.NO_SHOW,
               BookingStatus.CHECKED_OUT):
        _mk_booking(db, room, D(2026, 10, 1), D(2026, 10, 5), status=st)

    assert AvailabilityService(db).count_available(
        std.id, D(2026, 10, 1), D(2026, 10, 5)) == 3


def test_het_phong_thi_khong_hien_thi(db):
    _mk_booking(db, _std_rooms(db), D(2026, 10, 1), D(2026, 10, 5))

    res = AvailabilityService(db).search(D(2026, 10, 1), D(2026, 10, 5), guests=1)
    assert "Standard" not in [r.name for r in res.room_types]


def test_exclude_booking_khi_sua(db):
    """Khi sửa booking, không được tính chính nó là đang chiếm phòng."""
    std = _std(db)
    b = _mk_booking(db, _std_rooms(db), D(2026, 10, 1), D(2026, 10, 5))

    svc = AvailabilityService(db)
    assert svc.count_available(std.id, D(2026, 10, 1), D(2026, 10, 5)) == 0
    assert svc.count_available(std.id, D(2026, 10, 1), D(2026, 10, 5),
                               exclude_booking_id=b.id) == 3


def test_free_rooms_tra_ve_phong_cu_the(db):
    std = _std(db)
    rooms = AvailabilityService(db).free_rooms(std.id, D(2026, 10, 1), D(2026, 10, 5))
    assert sorted(r.room_number for r in rooms) == ["101", "102", "103"]


def test_free_rooms_bo_phong_da_dat(db):
    """Đã đặt phòng 101 thì chỉ còn 102, 103 — biết chính xác phòng nào bận."""
    std = _std(db)
    _mk_booking(db, _std_rooms(db)[:1], D(2026, 10, 3), D(2026, 10, 7))

    rooms = AvailabilityService(db).free_rooms(std.id, D(2026, 10, 1), D(2026, 10, 5))
    assert sorted(r.room_number for r in rooms) == ["102", "103"]


def test_search_liet_ke_phong_cu_the(db):
    _mk_booking(db, _std_rooms(db)[:1], D(2026, 10, 3), D(2026, 10, 7))

    res = AvailabilityService(db).search(D(2026, 10, 1), D(2026, 10, 5), guests=1)
    std = next(r for r in res.room_types if r.name == "Standard")
    assert std.available_count == 2
    assert sorted(r.room_number for r in std.rooms) == ["102", "103"]


def test_tong_tien_bang_tong_gia_tung_dem(db):
    res = AvailabilityService(db).search(D(2026, 10, 1), D(2026, 10, 5), guests=1)
    std = next(r for r in res.room_types if r.name == "Standard")
    assert len(std.nightly_rates) == 4
    assert std.total_price == sum(n.price for n in std.nightly_rates)
    assert res.nights == 4
