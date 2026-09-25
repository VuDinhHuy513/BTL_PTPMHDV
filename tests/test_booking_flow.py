"""Integration test: chạy trọn luồng nghiệp vụ qua HTTP API.

Booking do nhân viên tạo, chọn đúng phòng (room_ids). Không có tiền cọc.
"""

from tests.helpers import require_models

require_models("Booking", "BookingDetail", "BookingNightRate", "Customer", "Invoice", "Payment", "Service")

import datetime as dt

BASE = "/api/v1"


def _std_id(client, auth):
    r = client.get(f"{BASE}/room-types", headers=auth)
    return next(t["id"] for t in r.json()["data"] if t["name"] == "Standard")


def _std_rooms(client, auth):
    """Id các phòng Standard, xếp theo số phòng: 101, 102, 103."""
    r = client.get(f"{BASE}/rooms", headers=auth,
                   params={"room_type_id": _std_id(client, auth)})
    rooms = sorted(r.json()["data"], key=lambda x: x["room_number"])
    return [x["id"] for x in rooms]


def _make_booking(client, auth, ci, co, room_ids, guests=1, phone="0912345678"):
    return client.post(f"{BASE}/bookings", headers=auth, json={
        "customer": {"full_name": "Nguyễn Văn Test", "phone": phone},
        "check_in": ci.isoformat(), "check_out": co.isoformat(),
        "guests": guests, "room_ids": room_ids,
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
    ids = _std_rooms(client, auth)
    r = _make_booking(client, auth, tomorrow + dt.timedelta(days=3), tomorrow, ids[:1])
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_khong_dat_duoc_ngay_qua_khu(client, auth):
    ids = _std_rooms(client, auth)
    yesterday = dt.date.today() - dt.timedelta(days=1)
    r = _make_booking(client, auth, yesterday, yesterday + dt.timedelta(days=2), ids[:1])
    assert r.status_code == 422


def test_khong_chon_trung_phong_trong_mot_booking(client, auth, tomorrow):
    ids = _std_rooms(client, auth)
    r = _make_booking(client, auth, tomorrow, tomorrow + dt.timedelta(days=2),
                      [ids[0], ids[0]])
    assert r.status_code == 422


def test_so_khach_vuot_suc_chua(client, auth, tomorrow):
    """2 phòng Standard (mỗi phòng chứa 2) thì tối đa 4 khách."""
    ids = _std_rooms(client, auth)
    r = _make_booking(client, auth, tomorrow, tomorrow + dt.timedelta(days=2),
                      ids[:2], guests=5)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "GUESTS_EXCEED_CAPACITY"


# ----------------------------------------------------------- luồng chính
def test_tron_luong_dat_nhan_dung_dich_vu_tra_phong(client, auth, tomorrow):
    ci, co = dt.date.today(), tomorrow + dt.timedelta(days=2)
    ids = _std_rooms(client, auth)

    # 1. Tra phòng trống: thấy đúng phòng cụ thể
    r = client.get(f"{BASE}/availability", headers=auth, params={
        "check_in": ci.isoformat(), "check_out": co.isoformat(), "guests": 1})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["nights"] == (co - ci).days
    std = next(t for t in data["room_types"] if t["name"] == "Standard")
    assert std["available_count"] == 3
    assert [x["room_number"] for x in std["rooms"]] == ["101", "102", "103"]
    assert len(std["nightly_rates"]) == data["nights"]

    # 2. Nhân viên đặt đúng phòng 101
    r = _make_booking(client, auth, ci, co, [ids[0]])
    assert r.status_code == 201, r.text
    booking = r.json()["data"]
    assert booking["status"] == "Confirmed"
    assert booking["code"].startswith("BK")
    assert booking["details"][0]["room_id"] == ids[0]
    bid = booking["id"]

    # 3. Sau khi đặt, phòng 101 không còn trong danh sách trống
    r = client.get(f"{BASE}/availability", headers=auth, params={
        "check_in": ci.isoformat(), "check_out": co.isoformat(), "guests": 1})
    std = next(t for t in r.json()["data"]["room_types"] if t["name"] == "Standard")
    assert std["available_count"] == 2
    assert [x["room_number"] for x in std["rooms"]] == ["102", "103"]

    # 4. Check-in — phòng đã có từ lúc đặt, không cần gán lại
    r = client.post(f"{BASE}/bookings/{bid}/check-in", headers=auth,
                    json={"id_card_number": "012345678901"})
    assert r.status_code == 200, r.text
    b = r.json()["data"]
    assert b["status"] == "CheckedIn"
    assert b["details"][0]["room_id"] == ids[0]
    assert b["details"][0]["room_number"] == "101"
    room_id = ids[0]

    # phòng đã chuyển sang Occupied
    r = client.get(f"{BASE}/rooms/{room_id}", headers=auth)
    assert r.json()["data"]["status"] == "Occupied"

    # 5. Ghi nhận dịch vụ
    svc_id = client.get(f"{BASE}/services", headers=auth).json()["data"][0]["id"]
    r = client.post(f"{BASE}/bookings/{bid}/services", headers=auth,
                    json={"service_id": svc_id, "quantity": 2})
    assert r.status_code == 201
    assert float(r.json()["data"]["amount"]) == 200000

    # 6. Folio: tiền phòng + dịch vụ + VAT (không có cọc)
    r = client.get(f"{BASE}/bookings/{bid}/folio", headers=auth)
    folio = r.json()["data"]
    nights = (co - ci).days
    assert float(folio["room_charge"]) == 500000 * nights
    assert float(folio["service_charge"]) == 200000
    assert float(folio["subtotal"]) == 500000 * nights + 200000
    assert float(folio["vat_amount"]) == round(float(folio["subtotal"]) * 0.08, 2)
    assert float(folio["balance_due"]) == float(folio["total"])

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

    # 9. Phòng chuyển sang Dirty (lễ tân tự gọi buồng phòng dọn ngoài hệ thống)
    r = client.get(f"{BASE}/rooms/{room_id}", headers=auth)
    assert r.json()["data"]["status"] == "Dirty"

    # 10. Dọn xong, lễ tân đổi phòng về Available
    r = client.patch(f"{BASE}/rooms/{room_id}/status", headers=auth,
                     json={"status": "Available"})
    assert r.status_code == 200
    r = client.get(f"{BASE}/rooms/{room_id}", headers=auth)
    assert r.json()["data"]["status"] == "Available"


def test_khach_cu_duoc_dung_lai_theo_so_dien_thoai(client, auth, tomorrow):
    ids = _std_rooms(client, auth)
    ci, co = tomorrow, tomorrow + dt.timedelta(days=1)
    b1 = _make_booking(client, auth, ci, co, [ids[0]]).json()["data"]
    b2 = _make_booking(client, auth, ci, co, [ids[1]]).json()["data"]
    assert b1["customer"]["id"] == b2["customer"]["id"]


# ------------------------------------------------------- chống overbooking
def test_khong_dat_duoc_phong_da_co_nguoi_dat(client, auth, tomorrow):
    ci, co = tomorrow, tomorrow + dt.timedelta(days=2)
    ids = _std_rooms(client, auth)

    r = _make_booking(client, auth, ci, co, ids, guests=3)      # cả 3 phòng
    assert r.status_code == 201

    # phòng 101 đã có người → phải bị từ chối
    r = _make_booking(client, auth, ci, co, [ids[0]])
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ROOM_NOT_AVAILABLE"


def test_dat_trung_mot_phan_khoang_ngay_bi_tu_choi(client, auth, tomorrow):
    ids = _std_rooms(client, auth)
    ci, co = tomorrow, tomorrow + dt.timedelta(days=3)
    assert _make_booking(client, auth, ci, co, [ids[0]]).status_code == 201

    # gối đầu 1 ngày vẫn là trùng
    r = _make_booking(client, auth, ci + dt.timedelta(days=2),
                      co + dt.timedelta(days=2), [ids[0]])
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ROOM_NOT_AVAILABLE"

    # phòng khác thì vẫn đặt được
    assert _make_booking(client, auth, ci, co, [ids[1]]).status_code == 201


def test_khong_dat_duoc_phong_bao_tri(client, auth, tomorrow):
    r = client.get(f"{BASE}/rooms", headers=auth, params={"status": "OutOfOrder"})
    room_id = r.json()["data"][0]["id"]
    r = _make_booking(client, auth, tomorrow, tomorrow + dt.timedelta(days=1), [room_id])
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ROOM_NOT_AVAILABLE"


def test_dat_duoc_ngay_sau_khi_khach_cu_tra_phong(client, auth, tomorrow):
    """Case biên: nhận phòng đúng ngày khách cũ trả phòng."""
    ci, co = tomorrow, tomorrow + dt.timedelta(days=2)
    ids = _std_rooms(client, auth)
    assert _make_booking(client, auth, ci, co, ids, guests=3).status_code == 201

    # khoảng ngày nối tiếp, không giao nhau → phải đặt được
    r = _make_booking(client, auth, co, co + dt.timedelta(days=2), ids, guests=3)
    assert r.status_code == 201, r.text


# --------------------------------------------------- vòng đời trạng thái
def test_khong_check_in_booking_da_huy(client, auth, tomorrow):
    ids = _std_rooms(client, auth)
    r = _make_booking(client, auth, dt.date.today(), tomorrow, ids[:1])
    bid = r.json()["data"]["id"]

    r = client.post(f"{BASE}/bookings/{bid}/cancel", headers=auth,
                    json={"reason": "Khách đổi kế hoạch"})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "Cancelled"

    r = client.post(f"{BASE}/bookings/{bid}/check-in", headers=auth, json={})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_khong_check_in_truoc_ngay_nhan_phong(client, auth, tomorrow):
    ids = _std_rooms(client, auth)
    r = _make_booking(client, auth, tomorrow + dt.timedelta(days=5),
                      tomorrow + dt.timedelta(days=7), ids[:1])
    bid = r.json()["data"]["id"]

    r = client.post(f"{BASE}/bookings/{bid}/check-in", headers=auth, json={})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "TOO_EARLY_TO_CHECK_IN"


def test_check_in_phong_chua_don_bi_tu_choi(client, auth, tomorrow):
    """Phòng đang Dirty thì chưa nhận khách được."""
    ids = _std_rooms(client, auth)
    r = _make_booking(client, auth, dt.date.today(), tomorrow, ids[:1])
    bid = r.json()["data"]["id"]

    r = client.patch(f"{BASE}/rooms/{ids[0]}/status", headers=auth,
                     json={"status": "Dirty"})
    assert r.status_code == 200

    r = client.post(f"{BASE}/bookings/{bid}/check-in", headers=auth, json={})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ROOM_NOT_READY"


def test_huy_booking_da_huy_thi_bao_loi(client, auth, tomorrow):
    ids = _std_rooms(client, auth)
    r = _make_booking(client, auth, dt.date.today(), tomorrow, ids[:1])
    bid = r.json()["data"]["id"]
    client.post(f"{BASE}/bookings/{bid}/cancel", headers=auth, json={"reason": "x"})
    r = client.post(f"{BASE}/bookings/{bid}/cancel", headers=auth, json={"reason": "y"})
    assert r.status_code == 409


def test_booking_da_huy_nha_lai_phong(client, auth, tomorrow):
    ci, co = tomorrow, tomorrow + dt.timedelta(days=2)
    ids = _std_rooms(client, auth)
    r = _make_booking(client, auth, ci, co, ids, guests=3)
    bid = r.json()["data"]["id"]

    client.post(f"{BASE}/bookings/{bid}/cancel", headers=auth, json={"reason": "x"})

    # hủy xong thì đặt lại được, và nhả cả kỳ ở
    assert _make_booking(client, auth, ci, co, ids, guests=3).status_code == 201


def test_no_show_truoc_ngay_nhan_phong_bi_tu_choi(client, auth, tomorrow):
    ids = _std_rooms(client, auth)
    r = _make_booking(client, auth, tomorrow + dt.timedelta(days=3),
                      tomorrow + dt.timedelta(days=4), ids[:1])
    bid = r.json()["data"]["id"]

    r = client.post(f"{BASE}/bookings/{bid}/no-show", headers=auth)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "TOO_EARLY_TO_NO_SHOW"


def test_no_show_nha_lai_phong_cho_ca_ky_o(client, auth, tomorrow):
    ids = _std_rooms(client, auth)
    ci, co = dt.date.today(), dt.date.today() + dt.timedelta(days=3)
    r = _make_booking(client, auth, ci, co, ids[:1])
    bid = r.json()["data"]["id"]

    r = client.post(f"{BASE}/bookings/{bid}/no-show", headers=auth)
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "NoShow"

    # cả 3 đêm đều trống lại
    assert _make_booking(client, auth, ci, co, ids[:1]).status_code == 201


# ------------------------------------------------------------- đổi phòng
def test_doi_phong_khi_chua_check_in(client, auth, tomorrow):
    ids = _std_rooms(client, auth)
    ci, co = tomorrow, tomorrow + dt.timedelta(days=2)
    b = _make_booking(client, auth, ci, co, [ids[0]]).json()["data"]

    r = client.post(f"{BASE}/bookings/{b['id']}/change-room", headers=auth, json={
        "booking_detail_id": b["details"][0]["id"], "new_room_id": ids[1],
        "reason": "Khách muốn phòng tầng cao"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["details"][0]["room_id"] == ids[1]

    # phòng cũ được nhả, phòng mới bị giữ
    assert _make_booking(client, auth, ci, co, [ids[0]]).status_code == 201
    assert _make_booking(client, auth, ci, co, [ids[1]]).status_code == 409


# ------------------------------------------------------------- walk-in
def test_walk_in_tao_va_nhan_phong_ngay(client, auth):
    today = dt.date.today()
    ids = _std_rooms(client, auth)
    r = client.post(f"{BASE}/bookings/walk-in", headers=auth, json={
        "customer": {"full_name": "Khách vãng lai", "phone": "0987654321"},
        "check_out": (today + dt.timedelta(days=1)).isoformat(),
        "guests": 1, "room_ids": [ids[0]]})
    assert r.status_code == 201, r.text
    b = r.json()["data"]
    assert b["status"] == "CheckedIn"
    assert b["details"][0]["room_id"] == ids[0]


# ------------------------------------------------------------- sơ đồ phòng
def test_so_do_phong_theo_ngay(client, auth, tomorrow):
    ids = _std_rooms(client, auth)
    ci, co = tomorrow, tomorrow + dt.timedelta(days=2)
    b = _make_booking(client, auth, ci, co, [ids[0]]).json()["data"]

    r = client.get(f"{BASE}/rooms/schedule", headers=auth, params={
        "from": ci.isoformat(), "to": co.isoformat()})
    assert r.status_code == 200
    rows = {x["room_number"]: x for x in r.json()["data"]}
    assert [x["code"] for x in rows["101"]["bookings"]] == [b["code"]]
    assert rows["102"]["bookings"] == []


# ------------------------------------------------------------- báo cáo
def test_dashboard_va_bao_cao_chay_duoc(client, auth, tomorrow):
    ids = _std_rooms(client, auth)
    _make_booking(client, auth, dt.date.today(), tomorrow + dt.timedelta(days=1), ids[:1])

    r = client.get(f"{BASE}/reports/dashboard", headers=auth)
    assert r.status_code == 200
    assert r.json()["data"]["total_rooms"] == 5

    r = client.get(f"{BASE}/reports/arrivals", headers=auth,
                   params={"date": dt.date.today().isoformat()})
    assert r.status_code == 200
