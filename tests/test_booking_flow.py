"""Integration test: chạy trọn luồng nghiệp vụ qua HTTP API."""

from tests.helpers import require_models

require_models("Booking", "BookingDetail", "BookingNightRate", "Customer", "Invoice", "Payment", "Service")

import datetime as dt

BASE = "/api/v1"


def _std_id(client, auth):
    r = client.get(f"{BASE}/room-types", headers=auth)
    return next(t["id"] for t in r.json()["data"] if t["name"] == "Standard")


def _make_booking(client, auth, ci, co, qty=1, guests=1):
    return client.post(f"{BASE}/bookings", headers=auth, json={
        "customer": {"full_name": "Nguyễn Văn Test", "phone": "0912345678"},
        "check_in": ci.isoformat(), "check_out": co.isoformat(),
        "guests": guests,
        "lines": [{"room_type_id": _std_id(client, auth), "quantity": qty}],
        "deposit": "500000",
    })


# ------------------------------------------------------------------- auth
def test_login_sai_mat_khau(client):
    r = client.post(f"{BASE}/auth/login",
                    json={"username": "letan", "password": "sai-mat-khau"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_khong_co_token_thi_bi_chan(client):
    r = client.get(f"{BASE}/bookings")
    assert r.status_code == 401


def test_le_tan_khong_tao_duoc_loai_phong(client, auth):
    """Phân quyền: chỉ Admin mới được tạo loại phòng."""
    r = client.post(f"{BASE}/room-types", headers=auth,
                    json={"name": "X", "capacity": 2, "base_price": "100000"})
    assert r.status_code == 403


# --------------------------------------------------------------- validation
def test_checkout_truoc_checkin_bi_tu_choi(client, auth, tomorrow):
    r = _make_booking(client, auth, tomorrow + dt.timedelta(days=3), tomorrow)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_khong_dat_duoc_ngay_qua_khu(client, auth):
    yesterday = dt.date.today() - dt.timedelta(days=1)
    r = _make_booking(client, auth, yesterday, yesterday + dt.timedelta(days=2))
    assert r.status_code == 422


# ----------------------------------------------------------- luồng chính
def test_tron_luong_dat_nhan_dung_dich_vu_tra_phong(client, auth, tomorrow):
    ci, co = dt.date.today(), tomorrow + dt.timedelta(days=2)

    # 1. Tra phòng trống
    r = client.get(f"{BASE}/availability", headers=auth, params={
        "check_in": ci.isoformat(), "check_out": co.isoformat(), "guests": 1})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["nights"] == (co - ci).days
    std = next(t for t in data["room_types"] if t["name"] == "Standard")
    assert std["available_count"] == 3
    assert len(std["nightly_rates"]) == data["nights"]

    # 2. Đặt phòng
    r = _make_booking(client, auth, ci, co)
    assert r.status_code == 201, r.text
    booking = r.json()["data"]
    assert booking["status"] == "Confirmed"
    assert booking["code"].startswith("BK")
    bid = booking["id"]

    # 3. Sau khi đặt, số phòng trống giảm đi 1
    r = client.get(f"{BASE}/availability", headers=auth, params={
        "check_in": ci.isoformat(), "check_out": co.isoformat(), "guests": 1})
    std = next(t for t in r.json()["data"]["room_types"] if t["name"] == "Standard")
    assert std["available_count"] == 2

    # 4. Check-in — hệ thống tự gán phòng vật lý
    r = client.post(f"{BASE}/bookings/{bid}/check-in", headers=auth,
                    json={"id_card_number": "012345678901"})
    assert r.status_code == 200, r.text
    b = r.json()["data"]
    assert b["status"] == "CheckedIn"
    assert b["details"][0]["room_id"] is not None
    assert b["details"][0]["room_number"] is not None
    room_id = b["details"][0]["room_id"]

    # phòng đã chuyển sang Occupied
    r = client.get(f"{BASE}/rooms/{room_id}", headers=auth)
    assert r.json()["data"]["status"] == "Occupied"

    # 5. Ghi nhận dịch vụ
    svc_id = client.get(f"{BASE}/services", headers=auth).json()["data"][0]["id"]
    r = client.post(f"{BASE}/bookings/{bid}/services", headers=auth,
                    json={"service_id": svc_id, "quantity": 2})
    assert r.status_code == 201
    assert float(r.json()["data"]["amount"]) == 200000

    # 6. Folio: tiền phòng + dịch vụ + VAT
    r = client.get(f"{BASE}/bookings/{bid}/folio", headers=auth)
    folio = r.json()["data"]
    nights = (co - ci).days
    assert float(folio["room_charge"]) == 500000 * nights
    assert float(folio["service_charge"]) == 200000
    assert float(folio["subtotal"]) == 500000 * nights + 200000
    assert float(folio["vat_amount"]) == round(float(folio["subtotal"]) * 0.08, 2)
    # còn phải trả = tổng − cọc
    assert float(folio["balance_due"]) == float(folio["total"]) - 500000

    # 7. Thanh toán
    r = client.post(f"{BASE}/bookings/{bid}/payments", headers=auth,
                    json={"amount": folio["balance_due"], "method": "Cash"})
    assert r.status_code == 201

    r = client.get(f"{BASE}/bookings/{bid}/folio", headers=auth)
    assert float(r.json()["data"]["balance_due"]) == 0

    # 8. Check-out → xuất hóa đơn
    r = client.post(f"{BASE}/bookings/{bid}/check-out", headers=auth)
    assert r.status_code == 200, r.text
    invoice = r.json()["data"]
    assert invoice["code"].startswith("INV")
    assert float(invoice["total"]) == float(folio["total"])

    # 9. Phòng chuyển sang Dirty và có task dọn phòng
    r = client.get(f"{BASE}/rooms/{room_id}", headers=auth)
    assert r.json()["data"]["status"] == "Dirty"


# ------------------------------------------------------- chống overbooking
def test_khong_dat_duoc_qua_so_phong_con_lai(client, auth, tomorrow):
    ci, co = tomorrow, tomorrow + dt.timedelta(days=2)

    r = _make_booking(client, auth, ci, co, qty=3)
    assert r.status_code == 201

    # phòng thứ 4 không tồn tại → phải bị từ chối
    r = _make_booking(client, auth, ci, co, qty=1)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ROOM_NOT_AVAILABLE"


def test_dat_duoc_ngay_sau_khi_khach_cu_tra_phong(client, auth, tomorrow):
    """Case biên: nhận phòng đúng ngày khách cũ trả phòng."""
    ci, co = tomorrow, tomorrow + dt.timedelta(days=2)
    assert _make_booking(client, auth, ci, co, qty=3).status_code == 201

    # khoảng ngày nối tiếp, không giao nhau → phải đặt được
    r = _make_booking(client, auth, co, co + dt.timedelta(days=2), qty=3)
    assert r.status_code == 201, r.text


# --------------------------------------------------- vòng đời trạng thái
def test_khong_check_in_booking_da_huy(client, auth, tomorrow):
    r = _make_booking(client, auth, dt.date.today(), tomorrow)
    bid = r.json()["data"]["id"]

    r = client.post(f"{BASE}/bookings/{bid}/cancel", headers=auth,
                    json={"reason": "Khách đổi kế hoạch"})
    assert r.status_code == 200
    assert r.json()["data"]["booking"]["status"] == "Cancelled"

    r = client.post(f"{BASE}/bookings/{bid}/check-in", headers=auth, json={})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_khong_check_in_truoc_ngay_nhan_phong(client, auth, tomorrow):
    r = _make_booking(client, auth, tomorrow + dt.timedelta(days=5),
                      tomorrow + dt.timedelta(days=7))
    bid = r.json()["data"]["id"]

    r = client.post(f"{BASE}/bookings/{bid}/check-in", headers=auth, json={})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "TOO_EARLY_TO_CHECK_IN"


def test_huy_booking_da_huy_thi_bao_loi(client, auth, tomorrow):
    r = _make_booking(client, auth, dt.date.today(), tomorrow)
    bid = r.json()["data"]["id"]
    client.post(f"{BASE}/bookings/{bid}/cancel", headers=auth, json={"reason": "x"})
    r = client.post(f"{BASE}/bookings/{bid}/cancel", headers=auth, json={"reason": "y"})
    assert r.status_code == 409


def test_booking_da_huy_nha_lai_phong(client, auth, tomorrow):
    ci, co = tomorrow, tomorrow + dt.timedelta(days=2)
    r = _make_booking(client, auth, ci, co, qty=3)
    bid = r.json()["data"]["id"]

    client.post(f"{BASE}/bookings/{bid}/cancel", headers=auth, json={"reason": "x"})

    # hủy xong thì đặt lại được
    assert _make_booking(client, auth, ci, co, qty=3).status_code == 201


# ------------------------------------------------------------- walk-in
def test_walk_in_tao_va_nhan_phong_ngay(client, auth):
    today = dt.date.today()
    r = client.post(f"{BASE}/bookings/walk-in", headers=auth, json={
        "customer": {"full_name": "Khách vãng lai", "phone": "0987654321"},
        "check_in": today.isoformat(),
        "check_out": (today + dt.timedelta(days=1)).isoformat(),
        "guests": 1, "room_type_id": _std_id(client, auth), "quantity": 1,
        "deposit": "0"})
    assert r.status_code == 201, r.text
    b = r.json()["data"]
    assert b["status"] == "CheckedIn"
    assert b["details"][0]["room_id"] is not None


# ------------------------------------------------------------- báo cáo
def test_dashboard_va_bao_cao_chay_duoc(client, auth, tomorrow):
    _make_booking(client, auth, dt.date.today(), tomorrow + dt.timedelta(days=1))

    r = client.get(f"{BASE}/reports/dashboard", headers=auth)
    assert r.status_code == 200
    assert r.json()["data"]["total_rooms"] == 5

    r = client.get(f"{BASE}/reports/arrivals", headers=auth,
                   params={"date": dt.date.today().isoformat()})
    assert r.status_code == 200
