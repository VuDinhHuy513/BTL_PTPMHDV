"""Fixture dùng chung cho test.

=========================================================================
TEST TRONG THƯ MỤC NÀY LÀ "ĐỀ BÀI". Đừng sửa test cho khớp code — hãy sửa
code cho khớp test. Nếu thấy một test sai, kiểm tra lại
docs/BUSINESS_RULES.md trước khi kết luận.

Dữ liệu test cố định:
    Standard  sức chứa 2, giá 500.000 — 3 phòng (101, 102, 103)
    Deluxe    sức chứa 4, giá 1.000.000 — 2 phòng (201, và 202 đang BẢO TRÌ)
    1 dịch vụ "Ăn sáng" 100.000
    2 tài khoản: admin / letan

⚠ conftest.py import model từ app.models. Khi bạn chưa viết xong model nào
  thì bỏ import tương ứng ra, hoặc test sẽ lỗi ngay lúc collect.
=========================================================================
"""
import datetime as dt
import os
from decimal import Decimal

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_hotel.db"
os.environ["JWT_SECRET"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

# conftest.py KHÔNG được skip ở mức module (pytest không cho), nên import
# model muộn ở đây và để fixture `db` tự skip nếu còn thiếu.
REQUIRED_MODELS = ("Role", "Room", "RoomStatus", "RoomType", "Service", "User")
try:
    import app.models as _m
    from app.db.base import Base
    _missing = [n for n in REQUIRED_MODELS if not hasattr(_m, n)]
except Exception as _exc:                                   # noqa: BLE001
    Base, _m, _missing = None, None, [f"(lỗi import: {_exc})"]

TEST_URL = "sqlite:///./test_hotel.db"
engine = create_engine(TEST_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db():
    if _missing:
        pytest.skip("Chưa viết xong model: " + ", ".join(_missing)
                    + ". Viết xong rồi bỏ comment trong app/models/__init__.py.")
    Role, Room = _m.Role, _m.Room
    RoomStatus, RoomType = _m.RoomStatus, _m.RoomType
    Service, User = _m.Service, _m.User

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = TestSession()

    # 1 loại phòng Standard: 3 phòng, giá cơ bản 500k
    std = RoomType(name="Standard", capacity=2, base_price=Decimal("500000"))
    dlx = RoomType(name="Deluxe", capacity=4, base_price=Decimal("1000000"))
    session.add_all([std, dlx])
    session.flush()

    session.add_all([
        Room(room_number="101", floor=1, room_type_id=std.id),
        Room(room_number="102", floor=1, room_type_id=std.id),
        Room(room_number="103", floor=1, room_type_id=std.id),
        Room(room_number="201", floor=2, room_type_id=dlx.id),
        # phòng bảo trì — phải bị loại khỏi kết quả tra phòng trống
        Room(room_number="202", floor=2, room_type_id=dlx.id,
             status=RoomStatus.OUT_OF_ORDER),
    ])
    session.add(Service(name="Ăn sáng", unit="suất", unit_price=Decimal("100000")))
    session.add_all([
        User(username="admin", full_name="Admin",
             password_hash=hash_password("admin123"), role=Role.ADMIN),
        User(username="letan", full_name="Lễ tân",
             password_hash=hash_password("letan123"), role=Role.RECEPTIONIST),
    ])
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def token(client):
    r = client.post("/api/v1/auth/login",
                    json={"username": "letan", "password": "letan123"})
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


@pytest.fixture()
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def tomorrow():
    return dt.date.today() + dt.timedelta(days=1)
