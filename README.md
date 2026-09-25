# Hotel PMS API — Khung xương dự án

Khung xương cho đồ án website quản lý khách sạn, backend bằng **FastAPI +
SQLAlchemy 2.0**.

Repo này **cố tình để trống phần nghiệp vụ**. Hạ tầng đã dựng sẵn, còn logic
là việc của bạn. Test đã viết đủ — bạn code cho tới khi test xanh.

---

## 1. Cài đặt

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

pytest tests/test_smoke.py       # 3 test này phải xanh
uvicorn app.main:app --reload    # mở http://localhost:8000/docs
```

Nếu 3 test khói xanh và Swagger mở được, bạn đã sẵn sàng.

---

## 2. Cách làm việc với repo này

Chạy `pytest` bất cứ lúc nào để biết mình đang ở đâu:

```
3 passed, 3 skipped        ← mới bắt đầu, chưa viết model nào
```

Test tự bật lên theo tiến độ. Chạy `pytest -rs` để xem lý do skip:

```
SKIPPED [1] Chưa viết xong model: Booking, Customer. Viết xong rồi bỏ
            comment trong app/models/__init__.py.
```

Viết xong model → test bật lên và **đỏ** với `NotImplementedError` →
viết service → test **xanh**. Cứ thế đi hết.

**Test là đề bài.** Đừng sửa test cho khớp code. Nếu thấy test sai, đọc lại
`docs/BUSINESS_RULES.md` trước khi kết luận.

---

## 3. Ba tài liệu phải đọc

| File | Nội dung | Khi nào đọc |
|---|---|---|
| `docs/CONVENTIONS.md` | Quy tắc viết code: phân tầng, không hard-code, đặt tên, xử lý lỗi | **Trước khi gõ dòng đầu tiên** |
| `docs/BUSINESS_RULES.md` | Đặc tả nghiệp vụ R1–R12 — đây là đề bài | Mỗi lần bắt đầu một phần mới |
| `docs/API_SPEC.md` | Danh mục 57 endpoint cần làm | Khi viết tầng API |

---

## 4. File mẫu — đọc trước khi tự viết

Bốn file đã viết đầy đủ để bạn bắt chước:

| File | Mẫu cho |
|---|---|
| `app/models/room.py` | Cách khai báo model SQLAlchemy 2.0 |
| `app/schemas/room.py` | Cách viết DTO Pydantic (`*In` / `*Out`) |
| `app/api/v1/endpoints/room_types.py` | Cách viết endpoint đầy đủ CRUD |
| `app/core/deps.py` | Cách khai báo quyền bằng `Depends(require_*)` |

Phần hạ tầng đã xong, **không cần sửa**: `config.py`, `exceptions.py`,
`response.py`, `security.py`, `session.py`, `enums.py`, `main.py`.

---

## 5. Thứ tự làm

Làm đúng thứ tự này, mỗi bước đều chạy được trước khi sang bước sau.

### Bước 1 — Model (2–3 ngày)

Viết toàn bộ file trong `app/models/`. Mỗi file có sẵn checklist các trường.

Xong mỗi model thì bỏ comment dòng tương ứng trong `app/models/__init__.py`
**và** `app/db/base.py`.

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
pytest -rs          # test bắt đầu bật lên
```

Ba chỗ dễ sai:
- `BookingDetail.room_id` phải **NOT NULL** (nhân viên chọn đúng phòng lúc đặt) — xem R5
- Tiền dùng `Numeric(18, 2)`, không dùng `Float`
- Nhớ `Index` trên `(check_in, check_out, status)` của bảng `bookings`

### Bước 2 — PricingService (nửa ngày)

File `app/services/pricing_service.py`. Đích: `pytest tests/test_pricing.py` xanh.

Bẫy: `while d < check_out`, không phải `<=`. Ở 01/10 → 05/10 là **4 đêm**.

### Bước 3 — AvailabilityService (1–2 ngày) ⭐

File `app/services/availability_service.py`. Đích: `pytest tests/test_availability.py` xanh.

Đây là phần khó nhất về mặt truy vấn. Công thức giao nhau hai khoảng ngày:

```
booking.check_in < search_check_out  AND  booking.check_out > search_check_in
```

Dùng `<` và `>`, không phải `<=` và `>=`. Case biên: khách A trả phòng ngày 05,
khách B nhận phòng ngày 05 → không trùng.

### Bước 4 — Auth + endpoint danh mục (1–2 ngày)

`auth_service.py`, rồi `rooms.py`, `customers.py`, `services.py`,
`users.py`. Bắt chước `room_types.py`.

Bỏ comment dần trong `app/api/v1/router.py`.

### Bước 5 — BookingService (2–3 ngày) ⭐⭐

File `app/services/booking_service.py`. Đích: `pytest tests/test_booking_flow.py` xanh.

Phần khó nhất của cả đồ án: **chống overbooking**. Đọc kỹ `app/db/locking.py`
trước, trong đó có sơ đồ giải thích vấn đề.

### Bước 6 — Folio, thanh toán, báo cáo (2–3 ngày)

`folio_service.py`, `report_service.py`.

### Bước 7 — Seed + kiểm chứng (1 ngày)

Viết `scripts/seed.py` và `scripts/test_concurrent.py`. Cả hai file đều có
hướng dẫn chi tiết bên trong.

```bash
python -m scripts.seed
uvicorn app.main:app --port 8000     # terminal 1
python -m scripts.test_concurrent    # terminal 2
```

Kết quả mong đợi: bắn 12 request đồng thời cùng đặt **một phòng** (cùng khoảng ngày) →
**1 thành công, 11 bị từ chối 409**.

---

## 6. Cấu trúc thư mục

```
app/
├── main.py                 ✅ khởi động app, CORS, exception handler
├── core/
│   ├── config.py           ✅ đọc .env — nơi duy nhất chứa cấu hình
│   ├── exceptions.py       ✅ NotFoundError, BusinessError, ForbiddenError
│   ├── response.py         ✅ format response thống nhất
│   ├── security.py         ✅ hash mật khẩu, phát hành/giải mã JWT
│   └── deps.py             ✅ require_admin, require_front_desk…  (1 chỗ TODO)
├── db/
│   ├── session.py          ✅ engine, get_db
│   ├── base.py             ⬜ Base + import gom cho Alembic
│   └── locking.py          ⬜ chống overbooking — có sơ đồ giải thích
├── models/
│   ├── enums.py            ✅ Role, RoomStatus, BookingStatus…
│   ├── room.py             ✅ FILE MẪU
│   └── (5 file khác)       ⬜ có checklist trường bên trong
├── schemas/
│   ├── common.py           ✅
│   ├── room.py             ✅ FILE MẪU
│   ├── availability.py     ✅
│   └── (6 file khác)       ⬜
├── services/               ⬜ toàn bộ — có hướng dẫn từng bước trong docstring
└── api/v1/
    ├── router.py           ⬜ bỏ comment dần
    └── endpoints/
        ├── room_types.py   ✅ FILE MẪU
        └── (9 file khác)   ⬜ có danh mục endpoint bên trong

tests/                      ✅ đã viết đủ — đây là đề bài, đừng sửa
scripts/                    ⬜ seed và test đồng thời
docs/                       ✅ 3 tài liệu
```

---

## 7. Lỗi hay gặp

| Triệu chứng | Nguyên nhân |
|---|---|
| `alembic autogenerate` sinh file rỗng | Chưa import model trong `app/db/base.py` |
| Test báo `cannot import name X from app.models` | Chưa bỏ comment trong `app/models/__init__.py` |
| Số đêm ra sai 1 đơn vị | Dùng `<=` thay vì `<` trong vòng lặp ngày |
| Khách trả phòng và khách mới nhận cùng ngày bị báo trùng | Dùng `<=` / `>=` trong điều kiện giao nhau |
| Sửa booking báo hết phòng dù chỉ đổi ngày 1 hôm | Quên truyền `exclude_booking_id` |
| Sau khi đổi phòng, `room_number` vẫn là phòng cũ | Thiếu `.execution_options(populate_existing=True)` khi nạp lại booking |
| Test đồng thời ra 2 booking thành công | Kiểm tra phòng trống nằm ngoài khối khóa `FOR UPDATE`, hoặc đang chạy SQLite (không có khóa hàng) |
| `404` khi gọi `/bookings/walk-in` | Route `{id}` khai báo trước, nuốt mất `walk-in` |

---

## 8. Trước khi nộp

- [ ] `pytest` xanh toàn bộ, không còn SKIPPED
- [ ] `python -m scripts.seed` chạy được, DB có dữ liệu
- [ ] `scripts/test_concurrent.py` ra 1 thành công / N-1 từ chối
- [ ] Swagger `/docs` hiển thị đủ nhóm endpoint, nút Authorize dùng được
- [ ] Không còn `raise NotImplementedError` nào trong `app/`
- [ ] Không còn `print()` sót lại
- [ ] Đã đọc lại checklist cuối `docs/CONVENTIONS.md`
- [ ] Export Postman collection kèm báo cáo

---

## 9. Nếu bí

Thứ tự nên thử:
1. Đọc lại docstring của chính hàm đó — hầu hết đều có hướng dẫn từng bước
2. Đọc quy tắc nghiệp vụ tương ứng trong `docs/BUSINESS_RULES.md`
3. Đọc file mẫu cùng loại (`room.py`, `room_types.py`)
4. Đọc code test để biết chính xác hàm phải trả về cái gì
