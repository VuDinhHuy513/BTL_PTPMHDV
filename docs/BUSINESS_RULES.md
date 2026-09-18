# Đặc tả nghiệp vụ

Đây là "đề bài". Test trong `tests/` được viết đúng theo các quy tắc dưới đây —
code của bạn làm đúng thì test xanh.

---

## R1. Số đêm và khoảng nửa mở

Khoảng lưu trú là `[check_in, check_out)` — **không bao gồm** ngày trả phòng.

- Ở 01/10 → 05/10 = **4 đêm** (01, 02, 03, 04)
- Ở 01/10 → 02/10 = **1 đêm**
- `check_out` phải lớn hơn `check_in`, không cho phép bằng nhau

Tiền phòng = tổng giá của từng đêm trong khoảng đó. Đêm của ngày trả phòng không
tính tiền.

---

## R2. Giá phòng theo từng ngày

M��i loại phòng có `base_price`. Bảng `rate_prices` chứa giá override cho một
`(loại phòng, ngày)` cụ thể.

Quy tắc tra giá cho một đêm:
1. Có bản ghi trong `rate_prices` cho đúng `(room_type_id, date)` → lấy giá đó
2. Không có → lấy `room_type.base_price`

**Không được** tính `số_đêm × đơn_giá`. Khách ở từ thứ Năm đến Chủ Nhật sẽ đi qua
nhiều mức giá khác nhau.

Ví dụ: base 500k, ngày 02 và 03 override 650k, khách ở 01→05:
```
01/10: 500.000
02/10: 650.000
03/10: 650.000
04/10: 500.000
       ─────────
Tổng:  2.300.000    (không phải 4 × 500.000 = 2.000.000)
```

---

## R3. Phòng trống

M��t phòng bị coi là **đã chiếm** trong khoảng `[ci, co)` nếu tồn tại booking:
- có trạng thái `Confirmed` hoặc `CheckedIn`, VÀ
- chưa bị xóa mềm (`deleted_at IS NULL`), VÀ
- khoảng ngày **giao nhau** với `[ci, co)`

Công thức giao nhau hai khoảng:
```
booking.check_in  <  ci_tra_cuu_check_out
booking.check_out >  ci_tra_cuu_check_in
```

Dùng `<` và `>`, **không** dùng `<=` và `>=`.

**Case biên bắt buộc đúng:** khách A trả phòng ngày 05, khách B nhận phòng ngày 05
→ KHÔNG trùng nhau, phòng vẫn bán được.

Các trạng thái **không** chiếm phòng: `Pending`, `Cancelled`, `NoShow`, `CheckedOut`.

Phòng có trạng thái `OutOfOrder` (bảo trì) bị loại khỏi mọi kết quả tra phòng trống.

Kết quả trả về theo **loại phòng** ("còn 3 phòng Deluxe"), không phải phòng cụ thể.

---

## R4. Vòng đời booking

```
Pending ──→ Confirmed ──→ CheckedIn ──→ CheckedOut
   │            │
   ↓            ├──→ Cancelled
Cancelled       └──→ NoShow
```

Chuyển trạng thái nào không có trong sơ đồ → `BusinessError` với code
`INVALID_STATUS_TRANSITION`.

`CheckedOut`, `Cancelled`, `NoShow` là trạng thái cuối, không chuyển đi đâu được nữa.

---

## R5. Đặt phòng

- Lúc đặt, khách chỉ chọn **loại phòng** và số lượng. `booking_detail.room_id` để `NULL`.
- Giá từng đêm phải được **chốt** vào bảng `booking_night_rates` ngay lúc tạo.
- Không cho đặt ngày trong quá khứ.
- Một booking tối đa 60 đêm (tham số, đặt thành hằng số có tên).
- Nếu số phòng còn lại < số lượng yêu cầu → `BusinessError` code `ROOM_NOT_AVAILABLE`.

### Chống đặt trùng (overbooking)

Kiểm tra phòng trống rồi mới ghi là **không an toàn**: hai request đồng thời đều
đọc thấy "còn 1 phòng" trước khi request nào kịp ghi.

Phải: mở transaction → **khóa** theo `room_type_id` → kiểm tra lại số phòng trống
→ ghi → commit. Khóa tự nhả khi commit.

Khi đặt nhiều loại phòng cùng lúc, khóa theo thứ tự `room_type_id` tăng dần để
tránh deadlock.

Đây là phần khó nhất và cũng là phần ăn điểm nhất. Xem `app/db/locking.py`.

---

## R6. Sửa booking

- Chỉ sửa được khi trạng thái là `Pending` hoặc `Confirmed`.
- Đổi ngày phải **tính lại** giá từng đêm theo bảng giá hiện hành.
- Khi kiểm tra phòng trống cho ngày mới, phải **loại trừ chính booking đó** ra khỏi
  danh sách đang chiếm phòng — nếu không sẽ tự chặn chính mình.

---

## R7. Nhận phòng (check-in)

Điều kiện:
- Trạng thái hiện tại là `Confirmed`
- Chưa đến ngày nhận phòng → `BusinessError` code `TOO_EARLY_TO_CHECK_IN`

Các bước:
1. Gán phòng vật lý cho từng `booking_detail` (lễ tân chọn, hoặc hệ thống tự chọn phòng trống đầu tiên)
2. Kiểm tra phòng được gán: đúng loại, không bảo trì, đã dọn sạch, chưa có khách khác trong khoảng ngày
3. Ghi số giấy tờ tùy thân, cập nhật tiền cọc
4. Đổi trạng thái phòng sang `Occupied`
5. Đổi trạng thái booking sang `CheckedIn`, ghi `checked_in_at`

**Khách vãng lai (walk-in):** không có booking trước — tạo booking rồi check-in
ngay trong một lần gọi API.

---

## R8. Trả phòng (check-out)

1. Tổng hợp folio (xem R9), xuất hóa đơn
2. Đổi trạng thái phòng sang `Dirty`, tạo task dọn phòng
3. Đổi trạng thái booking sang `CheckedOut`, ghi `checked_out_at`

---

## R9. Folio và hóa đơn

```
Tiền phòng     = tổng booking_night_rates của mọi booking_detail
Tiền dịch vụ   = tổng (unit_price × quantity) của booking_services
─────────────────────────────────────────────────────────────
Tạm tính       = tiền phòng + tiền dịch vụ
VAT            = tạm tính × VAT_RATE        (lấy từ settings, KHÔNG viết 0.08)
Tổng cộng      = tạm tính + VAT
Còn phải trả   = tổng cộng − tiền cọc − đã thanh toán
```

Đơn giá dịch vụ cũng **chốt lúc ghi nhận**, không join sang bảng `services` khi
xuất hóa đơn.

Thanh toán cho phép nhiều lần, nhiều hình thức. Hoàn tiền lưu thành bản ghi
`payments` với số tiền **âm**.

---

## R10. Hủy booking

Chính sách: hủy trước `CANCEL_FREE_BEFORE_DAYS` ngày (lấy từ settings) thì hoàn
đủ tiền cọc, hủy muộn hơn thì mất cọc.

Hủy là **xóa mềm về mặt nghiệp vụ**: đổi trạng thái sang `Cancelled`, giữ nguyên
bản ghi. Không `DELETE` khỏi DB — sẽ mất dữ liệu báo cáo.

---

## R11. Phân quyền

| Vai trò | Được làm |
|---|---|
| `Admin` | Toàn quyền, quản lý user và bảng giá |
| `Receptionist` | Booking, check-in/out, thu tiền, xem danh mục |
| `Housekeeper` | Task dọn phòng, đổi trạng thái phòng |
| `Accountant` | Hóa đơn, folio, báo cáo (chỉ đọc) |

---

## R12. Báo cáo

```
Occupancy (%)  = số đêm-phòng đã bán / số đêm-phòng có thể bán × 100
ADR            = doanh thu phòng / số đêm-phòng đã bán
RevPAR         = doanh thu phòng / số đêm-phòng có thể bán
```

"Số đêm-phòng có thể bán" = số phòng không bảo trì × số ngày trong kỳ.

Doanh thu chỉ tính booking đã `CheckedIn` hoặc `CheckedOut`.
