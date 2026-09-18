# Quy tắc viết code

Đọc file này trước khi gõ dòng code đầu tiên. Mỗi quy tắc đều có lý do — nếu
không hiểu lý do thì đừng làm theo, hãy hỏi.

---

## 1. Quy tắc phân tầng — quan trọng nhất

```
Endpoint  →  Service  →  Model
(app/api)   (app/services)  (app/models)
```

Ba điều **không bao giờ** được vi phạm:

| Cấm | Vì sao |
|---|---|
| Endpoint viết `select()`, `db.query()` | Logic rò rỉ ra tầng HTTP, không test được nếu không dựng server |
| Service nhận `Request` hoặc trả `JSONResponse` | Service phải chạy được trong test, trong script CLI, trong job nền |
| Model chứa logic nghiệp vụ phức tạp | Model chỉ ánh xạ bảng. Property tính toán đơn giản (`nights`) thì được |

**Sai:**
```python
@router.get("/bookings")
def list_bookings(db: Session = Depends(get_db)):
    return db.query(Booking).filter(Booking.status == "Confirmed").all()
```

**Đúng:**
```python
@router.get("/bookings")
def list_bookings(db: Session = Depends(get_db), user=Depends(require_front_desk)):
    return ok(BookingService(db).list(status=BookingStatus.CONFIRMED))
```

Cách tự kiểm tra: mở file endpoint bất kỳ, nếu thấy `select(` hoặc `.filter(` thì
đã sai tầng.

---

## 2. Không hard-code

Ba loại giá trị hay bị viết cứng, và chỗ đúng của chúng:

| Loại | Sai | Đúng |
|---|---|---|
| Cấu hình môi trường | `engine = create_engine("postgresql://...")` | `.env` → `settings.DATABASE_URL` |
| Tham số nghiệp vụ | `total = subtotal * 1.08` | `.env` → `settings.VAT_RATE` |
| Giá trị cố định của domain | `if status == "Confirmed":` | `BookingStatus.CONFIRMED` (enum) |

Còn một loại thứ tư tinh vi hơn — **số ma thuật** (magic number):

```python
# Sai: 30 là gì? người đọc phải đoán
if (booking.check_out - booking.check_in).days > 30:

# Đúng
MAX_NIGHTS_PER_BOOKING = 30
if booking.nights > MAX_NIGHTS_PER_BOOKING:
```

Quy tắc đơn giản: nếu một số/chuỗi xuất hiện **quá 1 lần**, hoặc nếu người đọc
phải dừng lại hỏi "số này nghĩa là gì", thì đặt tên cho nó.

**Ngoại lệ hợp lý:** `0`, `1`, `""`, `[]` không cần đặt tên.

---

## 3. Enum thay vì chuỗi

M��i tập giá trị hữu hạn đều là enum. Xem `app/models/enums.py`.

```python
# Sai — gõ sai một chữ là bug im lặng, IDE không báo
booking.status = "Confimed"

# Đúng — gõ sai là lỗi ngay lúc import
booking.status = BookingStatus.CONFIRMED
```

---

## 4. Chốt giá (snapshot), không tính lại

Đây là quy tắc nghiệp vụ nhưng ảnh hưởng tới thiết kế bảng nên đặt ở đây.

Tiền phòng từng đêm và đơn giá dịch vụ phải được **lưu lại** vào bảng
`booking_night_rates` / `booking_services` tại thời điểm đặt.

Nếu hóa đơn join sang bảng giá hiện hành để tính, thì tháng sau sửa bảng giá sẽ
làm **đổi số tiền của những hóa đơn đã xuất từ trước**. Đó là lỗi nghiệp vụ nghiêm
trọng, không phải lỗi kỹ thuật.

---

## 5. Lỗi: raise, đừng return

Service `raise` exception, `app/main.py` bắt và biến thành JSON. Đừng trả về
`{"error": ...}` hay `None` để báo lỗi.

```python
# Sai
def get(self, booking_id):
    booking = self.db.get(Booking, booking_id)
    if not booking:
        return None           # caller phải nhớ kiểm tra None → dễ quên
    return booking

# Đúng
def get(self, booking_id):
    booking = self.db.get(Booking, booking_id)
    if not booking:
        raise NotFoundError("Booking", booking_id)
    return booking
```

Ba loại exception đã có sẵn trong `app/core/exceptions.py`:

| Lớp | HTTP | Dùng khi |
|---|---|---|
| `NotFoundError` | 404 | Không tìm thấy bản ghi |
| `BusinessError` | 409 | Vi phạm quy tắc nghiệp vụ (hết phòng, sai vòng đời trạng thái) |
| `ForbiddenError` | 403 | Không đủ quyền |

M��i `BusinessError` phải có `code` viết HOA_GACH_DUOI để frontend xử lý được:

```python
raise BusinessError("Loại phòng đã hết trong khoảng ngày này",
                    code="ROOM_NOT_AVAILABLE")
```

---

## 6. Đặt tên

| Loại | Quy ước | Ví dụ |
|---|---|---|
| File, hàm, biến | `snake_case` | `availability_service.py`, `get_nightly_rates` |
| Lớp | `PascalCase` | `BookingService`, `RoomType` |
| Hằng số | `UPPER_SNAKE` | `MAX_NIGHTS_PER_BOOKING` |
| Hàm private trong lớp | `_` đứng trước | `_validate_range` |
| Endpoint URL | `kebab-case`, danh từ số nhiều | `/room-types`, `/bookings/{id}/check-in` |

Hàm trả về `bool` bắt đầu bằng `is_`, `has_`, `can_`: `is_available`, `can_cancel`.

Biến ngày tháng luôn rõ nghĩa: `check_in` chứ không phải `d1`, `from_date`/`to_date`
chứ không phải `start`/`end` mập mờ.

---

## 7. Endpoint dạng hành động cho việc chuyển trạng thái

```python
# Sai — client có thể nhảy thẳng Pending → CheckedOut
PUT /bookings/1   { "status": "CheckedIn" }

# Đúng
POST /bookings/1/check-in   { "id_card_number": "...", "deposit": 500000 }
```

Lý do: check-in không chỉ đổi một trường. Nó gán phòng vật lý, ghi giấy tờ, thu
cọc, đổi trạng thái phòng sang `Occupied`. Đó là một **hành động**, không phải
phép cập nhật trường.

Quy tắc chung: dùng `PUT`/`PATCH` cho sửa dữ liệu thuần túy, dùng
`POST /{id}/{hành-động}` khi thao tác kéo theo nhiều thay đổi hoặc có điều kiện
nghiệp vụ.

---

## 8. Response thống nhất

M��i endpoint trả về qua hàm `ok()` trong `app/core/response.py`:

```python
{ "success": true, "data": {...}, "meta": null }
{ "success": true, "data": [...], "meta": {"page":1,"limit":20,"total":137} }
{ "success": false, "error": {"code":"...", "message":"..."} }
```

Đừng có endpoint này trả `{"data": ...}`, endpoint kia trả thẳng mảng. Frontend
sẽ phải viết code xử lý riêng cho từng cái.

M� HTTP: `200` đọc · `201` tạo mới · `401` chưa đăng nhập · `403` không đủ quyền ·
`404` không tìm thấy · `409` xung đột nghiệp vụ · `422` sai dữ liệu đầu vào.

---

## 9. Validate ở đúng chỗ

| Loại kiểm tra | Chỗ đúng | Ví dụ |
|---|---|---|
| Định dạng, kiểu, khoảng giá trị | Pydantic schema | `guests: int = Field(ge=1, le=20)` |
| Quan hệ giữa các trường trong cùng request | `@model_validator` | `check_out > check_in` |
| Cần truy vấn DB mới biết | Service | "còn đủ phòng không" |

Đừng viết kiểm tra định dạng trong service — Pydantic đã làm rồi, viết lại là thừa
và dễ lệch nhau.

---

## 10. Hàm ngắn, một việc

M��c tham khảo: hàm quá **40 dòng** thì dừng lại xem có tách được không. Không phải
luật cứng, nhưng hàm dài thường là dấu hiệu đang làm nhiều việc.

`BookingService.create()` dài vì nó điều phối nhiều bước — nhưng mỗi bước gọi một
hàm riêng (`_resolve_customer`, `_build_details`), nên đọc vẫn hiểu ngay.

---

## 11. Comment: giải thích TẠI SAO, không phải CÁI GÌ

```python
# Vô dụng — code đã nói rồi
d += timedelta(days=1)   # tăng d lên 1 ngày

# Có giá trị
while d < check_out:     # dùng <, không phải <=: đêm của ngày trả phòng
                         # không tính tiền. Ở 01→05 là 4 đêm, không phải 5.
```

Chỗ nào bạn phải suy nghĩ lâu mới ra, chỗ đó cần comment. Chỗ nào hiển nhiên thì
để yên.

Tiếng Việt hay tiếng Anh đều được, nhưng **nhất quán trong toàn dự án**.

---

## 12. Git

```
feat: them API tra cuu phong trong
fix: sua loi dem so dem sai khi tra phong
docs: cap nhat README
test: them test case bien tra/nhan phong cung ngay
refactor: tach PricingService khoi BookingService
```

Commit nhỏ, mỗi commit một việc. Không commit file `.env`, file `.db`, thư mục
`__pycache__` — đã có trong `.gitignore`.

---

## 13. Checklist trước khi commit

- [ ] `pytest` xanh
- [ ] Endpoint không chứa `select(` hay `.filter(`
- [ ] Không có chuỗi trạng thái viết tay (`"Confirmed"`) — dùng enum
- [ ] Không có số lạ không tên trong code
- [ ] Mỗi `BusinessError` đều có `code`
- [ ] Không có `print()` sót lại
- [ ] Không commit `.env`
