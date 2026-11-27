"""Tạo dữ liệu mẫu để demo.   Chạy: python -m scripts.seed  [--reset]

Ghi vào database mà DATABASE_URL đang trỏ tới (.env hoặc biến môi trường).

AN TOÀN: database đã có dữ liệu thì script DỪNG, không ghi đè. Muốn xóa sạch rồi
tạo lại thì chạy kèm --reset (xóa DỮ LIỆU trong các bảng, giữ nguyên cấu trúc).

Dữ liệu:
    - 2 tài khoản: admin/admin123 (Admin), letan/letan123 (Lễ tân)
    - 4 loại phòng, 20 phòng trên 4 tầng — giống hệt hotel_pms đang dùng
    - 4 dịch vụ: ăn sáng, giặt ủi, spa, gym
    - 12 khách (3 khách quen đặt nhiều lần)
    - 15 booking thiết kế TAY, ngày tính theo HÔM NAY, để mỗi chức năng đều có
      dữ liệu demo: đã trả phòng (có hóa đơn, có khách còn nợ, có hoàn tiền),
      đang ở, sắp đến hôm nay, tương lai, đã hủy, không đến, khách đoàn nhiều phòng.

Chạy lại ra CÙNG dữ liệu (random.seed cố định, ngày tính tương đối theo hôm nay).
"""
import argparse
import datetime as dt
import random
import sys
from decimal import Decimal

from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models import (Booking, BookingDetail, BookingNightRate, BookingSource,
                        BookingStatus, Customer, Invoice, Payment, PaymentMethod,
                        Role, Room, RoomStatus, RoomType, Service, User)
from app.models import BookingService as BookingServiceLine
from app.services.folio_service import FolioService

RANDOM_SEED = 42
CHECK_IN_HOUR = 14              # giờ nhận phòng / trả phòng điển hình của khách sạn
CHECK_OUT_HOUR = 12

# ------------------------------------------------------------------ danh mục
USERS = [("admin", "Quản trị viên", "admin123", Role.ADMIN),
         ("letan", "Lễ tân", "letan123", Role.RECEPTIONIST)]

# Giống hệt hotel_pms: (tên, sức chứa, giá/đêm)
ROOM_TYPES = {
    "Standard":  (2, "500000"),
    "Deluxe":    (4, "1000000"),
    "Vip":       (4, "1500000"),
    "Standard2": (4, "800000"),
}
# Giống hệt hotel_pms: số phòng → loại phòng (tầng = chữ số đầu)
ROOMS = {
    "101": "Standard", "102": "Standard", "103": "Standard", "104": "Standard",
    "105": "Standard",
    "201": "Standard2", "202": "Standard2", "203": "Standard2", "204": "Standard2",
    "205": "Standard",
    "301": "Deluxe", "302": "Deluxe", "303": "Standard2", "304": "Standard2",
    "305": "Standard2",
    "401": "Deluxe", "402": "Deluxe", "403": "Vip", "404": "Vip", "405": "Vip",
}

SERVICES = [("Ăn sáng", "suất", "100000"), ("Giặt ủi", "kg", "30000"),
            ("Spa", "lần", "350000"), ("Gym", "lượt", "50000")]

CUSTOMERS = [  # (họ tên, SĐT, email, CCCD)
    ("Nguyễn Văn An", "0912000001", "an.nguyen@gmail.com", "001090000001"),
    ("Trần Thị Bình", "0912000002", "binh.tran@gmail.com", "001090000002"),
    ("Công ty Du lịch Sao Mai", "0912000003", "booking@saomai.vn", None),
    ("Lê Hoàng Cường", "0912000004", None, "001090000004"),
    ("Phạm Thu Dung", "0912000005", "dung.pham@yahoo.com", "001090000005"),
    ("Hoàng Minh Đức", "0912000006", None, None),
    ("Vũ Thị Giang", "0912000007", "giang.vu@gmail.com", None),
    ("Đặng Quốc Huy", "0912000008", None, None),
    ("Bùi Thanh Hương", "0912000009", "huong.bui@gmail.com", "001090000009"),
    ("Đỗ Văn Khánh", "0912000010", None, "001090000010"),
    ("Ngô Thị Lan", "0912000011", "lan.ngo@gmail.com", "001090000011"),
    ("Dương Văn Minh", "0912000012", None, None),
]

# ------------------------------------------------------------------ 15 booking
# (khách, ngày đến, ngày đi tính từ HÔM NAY, phòng, số khách, trạng thái, thêm)
#   services: [(tên dịch vụ, số lượng, ngày dùng tính từ hôm nay)]
#   pay:      "full" trả đủ | "partial" trả một nửa | "none" chưa trả
#   refund:   số tiền thu dư rồi hoàn lại
S = BookingStatus
BOOKINGS = [
    # --- Đã trả phòng: có hóa đơn
    dict(c=0, ci=-25, co=-22, rooms=["101"], g=2, st=S.CHECKED_OUT, pay="full",
         method=PaymentMethod.CASH, services=[("Ăn sáng", 2, -24), ("Ăn sáng", 2, -23)]),
    dict(c=1, ci=-20, co=-18, rooms=["301"], g=3, st=S.CHECKED_OUT, pay="full",
         method=PaymentMethod.TRANSFER, services=[("Spa", 1, -19)]),
    dict(c=2, ci=-15, co=-12, rooms=["403", "404"], g=7, st=S.CHECKED_OUT, pay="full",
         method=PaymentMethod.TRANSFER, note="Khách đoàn công ty",
         services=[("Ăn sáng", 7, -14), ("Ăn sáng", 7, -13), ("Giặt ủi", 4, -13)]),
    dict(c=0, ci=-10, co=-7, rooms=["201"], g=2, st=S.CHECKED_OUT, pay="partial",
         method=PaymentMethod.CASH, note="Khách quen, hẹn chuyển khoản phần còn lại",
         services=[("Gym", 2, -9)]),
    dict(c=3, ci=-5, co=-3, rooms=["102"], g=1, st=S.CHECKED_OUT, pay="full",
         method=PaymentMethod.TRANSFER, refund="50000", services=[]),
    dict(c=4, ci=-2, co=0, rooms=["302"], g=2, st=S.CHECKED_OUT, pay="full",
         method=PaymentMethod.CARD, services=[("Ăn sáng", 2, -1)]),   # trả hôm nay → Dirty
    # --- Đã hủy / không đến
    dict(c=5, ci=-8, co=-6, rooms=["105"], g=2, st=S.CANCELLED,
         reason="Khách đổi lịch công tác"),
    dict(c=6, ci=10, co=12, rooms=["401"], g=2, st=S.CANCELLED,
         reason="Khách hủy chuyến bay"),
    dict(c=7, ci=-4, co=-2, rooms=["203"], g=2, st=S.NO_SHOW),
    # --- Đang ở: phòng Occupied
    dict(c=8, ci=-2, co=1, rooms=["103"], g=2, st=S.CHECKED_IN, pay="partial",
         method=PaymentMethod.CASH, services=[("Ăn sáng", 2, -1), ("Gym", 1, 0)]),
    dict(c=9, ci=-1, co=2, rooms=["405"], g=2, st=S.CHECKED_IN, pay="none",
         services=[("Spa", 2, 0)]),
    dict(c=10, ci=0, co=3, rooms=["202", "204"], g=5, st=S.CHECKED_IN, pay="none",
         note="Gia đình 5 người", services=[("Ăn sáng", 5, 0)]),
    # --- Sắp đến
    dict(c=11, ci=0, co=2, rooms=["104"], g=1, st=S.CONFIRMED),        # đến hôm nay
    dict(c=1, ci=3, co=5, rooms=["301"], g=2, st=S.CONFIRMED, note="Khách quen"),
    dict(c=2, ci=7, co=10, rooms=["402", "403"], g=6, st=S.CONFIRMED,
         note="Khách đoàn công ty, lần 2", source=BookingSource.STAFF),
]

# Xóa theo thứ tự con → cha để không vướng khóa ngoại
TABLES_CHILD_FIRST = [Payment, Invoice, BookingServiceLine, BookingNightRate,
                      BookingDetail, Booking, Customer, Service, Room, RoomType, User]
BLOCKING = (S.CONFIRMED, S.CHECKED_IN)


def _at(day: dt.date, hour: int) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(hour))


def _code(prefix: str, day: dt.date, rng: random.Random) -> str:
    # Dùng rng có seed thay vì secrets để chạy lại ra cùng mã
    return f"{prefix}{day:%y%m%d}-{rng.getrandbits(24):06X}"


def _ensure_no_overlap(plan) -> None:
    """Seed tự kiểm tra không tạo booking trùng phòng — cùng công thức < và >
    với hệ thống thật (R3). Không kiểm thì seed tạo ra chính lỗi overbooking."""
    busy: dict[str, list[tuple[int, int]]] = {}
    for b in plan:
        if b["st"] not in BLOCKING and b["st"] != S.CHECKED_OUT:
            continue
        for room in b["rooms"]:
            for start, end in busy.get(room, []):
                if b["ci"] < end and b["co"] > start:
                    sys.exit(f"Dữ liệu seed đặt trùng phòng {room}: ({b['ci']},{b['co']}) "
                             f"với ({start},{end})")
            busy.setdefault(room, []).append((b["ci"], b["co"]))


def _is_empty(db) -> bool:
    return all(db.scalar(select(func.count()).select_from(m)) == 0
               for m in (User, Room, Booking))


def _reset(db) -> None:
    for model in TABLES_CHILD_FIRST:
        db.execute(delete(model))
    db.commit()


def seed(db) -> None:
    rng = random.Random(RANDOM_SEED)
    today = dt.date.today()
    day = lambda offset: today + dt.timedelta(days=offset)   # noqa: E731

    for username, name, password, role in USERS:
        db.add(User(username=username, full_name=name, role=role,
                    password_hash=hash_password(password)))

    types = {name: RoomType(name=name, capacity=cap, base_price=Decimal(price))
             for name, (cap, price) in ROOM_TYPES.items()}
    db.add_all(types.values())
    db.flush()
    rooms = {number: Room(room_number=number, floor=int(number[0]),
                          room_type_id=types[type_name].id, status=RoomStatus.AVAILABLE)
             for number, type_name in ROOMS.items()}
    db.add_all(rooms.values())

    services = {name: Service(name=name, unit=unit, unit_price=Decimal(price))
                for name, unit, price in SERVICES}
    db.add_all(services.values())

    customers = [Customer(full_name=n, phone=p, email=e, id_card_number=cc)
                 for n, p, e, cc in CUSTOMERS]
    db.add_all(customers)
    db.flush()

    folio = FolioService(db)
    for plan in BOOKINGS:
        ci, co = day(plan["ci"]), day(plan["co"])
        created = _at(ci - dt.timedelta(days=rng.randint(3, 20)), rng.randint(8, 20))
        booking = Booking(
            code=_code("BK", created.date(), rng), customer_id=customers[plan["c"]].id,
            check_in=ci, check_out=co, guests=plan["g"], status=plan["st"],
            source=plan.get("source", BookingSource.STAFF), note=plan.get("note"),
            cancel_reason=plan.get("reason"), created_at=created)
        for number in plan["rooms"]:
            room = rooms[number]
            price = types[ROOMS[number]].base_price          # chốt giá từng đêm (R2)
            booking.details.append(BookingDetail(room_id=room.id, night_rates=[
                BookingNightRate(date=ci + dt.timedelta(days=i), price=price)
                for i in range((co - ci).days)]))
        if plan["st"] in (S.CHECKED_IN, S.CHECKED_OUT):
            booking.checked_in_at = _at(ci, CHECK_IN_HOUR)
        if plan["st"] == S.CHECKED_OUT:
            booking.checked_out_at = _at(co, CHECK_OUT_HOUR)
        db.add(booking)
        db.flush()

        for name, qty, offset in plan.get("services", []):
            svc = services[name]
            db.add(BookingServiceLine(booking_id=booking.id, service_id=svc.id,
                                      quantity=qty, used_date=day(offset),
                                      unit_price=svc.unit_price))   # chốt giá
        db.flush()
        _add_payments(db, folio, booking, plan, ci, co)

        if plan["st"] == S.CHECKED_OUT:
            invoice = folio.issue_invoice(booking)
            invoice.issued_at = _at(co, CHECK_OUT_HOUR)
            invoice.code = _code("INV", co, rng)
        # Trạng thái phòng khớp với booking
        for number in plan["rooms"]:
            if plan["st"] == S.CHECKED_IN:
                rooms[number].status = RoomStatus.OCCUPIED
            elif plan["st"] == S.CHECKED_OUT and co == today:
                rooms[number].status = RoomStatus.DIRTY          # vừa trả, chờ dọn
    db.commit()


def _add_payments(db, folio, booking, plan, ci, co) -> None:
    mode = plan.get("pay", "none")
    if mode == "none":
        return
    total = folio.build(booking.id).total
    amount = total if mode == "full" else (total / 2).quantize(Decimal("1"))
    refund = Decimal(plan.get("refund", "0"))
    paid_day = co if plan["st"] == S.CHECKED_OUT else ci
    receipt = Payment(booking_id=booking.id, amount=amount + refund,
                      method=plan["method"], paid_at=_at(paid_day, CHECK_OUT_HOUR - 1))
    db.add(receipt)
    db.flush()
    if refund:
        # Hoàn tiền = phiếu SỐ ÂM, cùng cách ghi với API /payments/{id}/refund
        db.add(Payment(booking_id=booking.id, amount=-refund, method=plan["method"],
                       note=f"Hoàn tiền phiếu thu #{receipt.id}: Khách chuyển dư",
                       paid_at=_at(paid_day, CHECK_OUT_HOUR)))
    db.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo dữ liệu mẫu cho Hotel PMS")
    parser.add_argument("--reset", action="store_true",
                        help="XÓA toàn bộ dữ liệu hiện có rồi tạo lại")
    args = parser.parse_args()

    print(f"Database: {engine.url.render_as_string(hide_password=True)}")
    _ensure_no_overlap(BOOKINGS)
    db = SessionLocal()
    try:
        if not _is_empty(db):
            if not args.reset:
                sys.exit("Database đã có dữ liệu → DỪNG, không ghi đè.\n"
                         "Muốn xóa sạch rồi tạo lại: python -m scripts.seed --reset")
            print("--reset: xóa dữ liệu cũ...")
            _reset(db)
        seed(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    counts = {m.__tablename__: SessionLocal().scalar(select(func.count()).select_from(m))
              for m in reversed(TABLES_CHILD_FIRST)}
    print("Xong:", ", ".join(f"{t}={n}" for t, n in counts.items()))
    print(f"VAT dùng cho hóa đơn: {settings.VAT_RATE}")
    print("Đăng nhập: admin/admin123 (Admin), letan/letan123 (Lễ tân)")


if __name__ == "__main__":
    main()
