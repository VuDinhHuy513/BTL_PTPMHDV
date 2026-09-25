# Đặc tả nghiệp vụ

Đây là "đề bài". Test trong `tests/` được viết đúng theo các quy tắc dưới đây —
code của bạn làm đúng thì test xanh.

**Bối cảnh:** khách sạn nhỏ, khách gọi điện hoặc đến quầy để đặt phòng. Toàn bộ
thao tác do **nhân viên** thực hiện trên hệ thống, không có khách tự đặt qua web.
Việc gọi buồng phòng dọn phòng làm ngoài đời, không quản lý trên hệ thống.

---

## R1. Số đêm và khoảng nửa mở

Khoảng lưu trú là `[check_in, check_out)` — **không bao gồm** ngày trả phòng.

- Ở 01/10 → 05/10 = **4 đêm** (01, 02, 03, 04)
- Ở 01/10 → 02/10 = **1 đêm**
- `check_out` phải lớn hơn `check_in`, không cho phép bằng nhau

Tiền phòng = tổng giá của từng đêm trong khoảng đó. Đêm của ngày trả phòng không
tính tiền.

---

## R2. Giá phòng

Mỗi loại phòng có một `base_price` **cố định** (giá một đêm). Không có giá theo
ngày, theo mùa hay cuối tuần.

Giá một đêm của một phòng = `base_price` của loại phòng đó.

Ví dụ: Standard 500k, khách ở 01→05 một phòng: 4 × 500.000 = 2.000.000.

Dù giá mọi đêm như nhau, giá vẫn được **chốt từng đêm** vào `booking_night_rates`
lúc tạo booking (xem R5): Admin sửa `base_price` sau này thì booking đã đặt không
đổi giá.

---

## R3. Phòng trống

Một **phòng cụ thể** bị coi là **đã chiếm** trong khoảng `[ci, co)` nếu tồn tại
booking giữ chính phòng đó (qua `booking_details.room_id`) mà:
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

Các trạng thái **không** chiếm phòng: `Cancelled`, `NoShow`, `CheckedOut`.

Phòng có trạng thái `OutOfOrder` (bảo trì) bị loại khỏi mọi kết quả tra phòng trống.
Các trạng thái `Occupied` / `Dirty` chỉ là tình trạng **hiện tại**, không loại phòng
khỏi kết quả tra cứu cho ngày sau (kiểm tra ở lúc check-in, xem R7).

Kết quả tra cứu gom theo **loại phòng**, mỗi loại kèm **danh sách phòng cụ thể** còn
trống ("Deluxe còn 2 phòng: 201, 203") để nhân viên chọn.

**Sơ đồ phòng theo ngày:** với một khoảng ngày, xem được từng phòng đang có những
booking nào (mã, khách, ngày đến, ngày đi). Đây là màn hình nhân viên xem khi khách
gọi điện.

---

## R4. Vòng đời booking

```
Confirmed ──→ CheckedIn ──→ CheckedOut
    │
    ├──→ Cancelled
    └──→ NoShow
```

Nhân viên đặt xong là chốt luôn, nên booking sinh ra ở trạng thái `Confirmed`
(nghĩa là "đã đặt trước"). Không có bước chờ duyệt.

Chuyển trạng thái nào không có trong sơ đồ → `BusinessError` với code
`INVALID_STATUS_TRANSITION`.

`CheckedOut`, `Cancelled`, `NoShow` là trạng thái cuối, không chuyển đi đâu được nữa.

---

## R5. Đặt phòng

- Khách gọi điện, **nhân viên chọn đúng phòng** (101, 102…) theo nhu cầu và gửi
  `room_ids`. Mỗi phòng là một dòng `booking_details`, `room_id` bắt buộc có.
- Thông tin khách: truyền `customer_id`, hoặc nhập họ tên + số điện thoại. Nếu số
  điện thoại đã có trong hệ thống thì **dùng lại khách cũ**, không tạo khách mới.
- Giá từng đêm của từng phòng phải được **chốt** vào bảng `booking_night_rates`
  ngay lúc tạo.
- Không cho đặt ngày trong quá khứ (`check_in` >= hôm nay).
- Một booking tối đa 60 đêm (tham số, đặt thành hằng số có tên).
- Không chọn trùng một phòng hai lần trong cùng booking (422).
- Số khách không được vượt tổng sức chứa các phòng đã chọn → `BusinessError` code
  `GUESTS_EXCEED_CAPACITY`.
- Phòng đã bận (hoặc đang `OutOfOrder`) trong khoảng ngày → `BusinessError` code
  `ROOM_NOT_AVAILABLE`.
- Booking mới có trạng thái `Confirmed`.

### Chống đặt trùng (overbooking)

Kiểm tra phòng trống rồi mới ghi là **không an toàn**: hai request đồng thời cùng
chọn phòng 101 đều đọc thấy "101 trống" trước khi request nào kịp ghi.

Phải: mở transaction → **khóa** các dòng phòng được chọn (`SELECT ... FOR UPDATE`)
→ kiểm tra lại phòng trống → ghi → commit. Khóa tự nhả khi commit.

Khi đặt nhiều phòng cùng lúc, khóa theo thứ tự `room_id` tăng dần để tránh deadlock.

Đây là phần khó nhất và cũng là phần ăn điểm nhất. Xem `app/db/locking.py`.

---

## R6. Sửa booking

- Chỉ sửa được khi trạng thái là `Confirmed`.
- Sửa được: ngày ở, số khách, ghi chú. Không sửa danh sách phòng ở đây — muốn đổi
  phòng dùng "đổi phòng" (R7).
- Đổi ngày phải kiểm tra **chính các phòng đang giữ** còn trống ở ngày mới, và phải
  **loại trừ chính booking đó** ra khỏi danh sách đang chiếm phòng — nếu không sẽ tự
  chặn chính mình.
- Đổi ngày phải **tính lại** giá từng đêm theo `base_price` hiện hành. Rút ngắn kỳ
  ở thì các đêm bị bỏ được nhả ra.

---

## R7. Nhận phòng (check-in) và đổi phòng

Điều kiện check-in:
- Trạng thái hiện tại là `Confirmed`
- Chưa đến ngày nhận phòng → `BusinessError` code `TOO_EARLY_TO_CHECK_IN`
  (đến muộn thì vẫn check-in được)
- Mọi phòng của booking đang `Available`. Phòng `Dirty` (chưa dọn), `Occupied`
  (khách cũ chưa trả) hoặc `OutOfOrder` → `BusinessError` code `ROOM_NOT_READY`

Các bước (phòng đã chọn từ lúc đặt nên không còn bước gán phòng):
1. Kiểm tra các điều kiện trên
2. Ghi số giấy tờ tùy thân vào hồ sơ khách
3. Đổi trạng thái phòng sang `Occupied`
4. Đổi trạng thái booking sang `CheckedIn`, ghi `checked_in_at`

**Khách vãng lai (walk-in):** không có booking trước — nhân viên chọn phòng đang
trống, hệ thống tạo booking (nhận phòng hôm nay) rồi check-in ngay trong một lần
gọi API, cùng một giao dịch.

**Đổi phòng:** dùng được khi booking `Confirmed` hoặc `CheckedIn`.
- Phòng mới phải trống cho các đêm còn lại (loại trừ chính booking).
- Booking `Confirmed`: chỉ đổi phòng gắn với booking.
- Booking `CheckedIn`: phòng cũ → `Dirty`, phòng mới (phải `Available`) → `Occupied`.
- Phòng mới khác loại/giá: tính lại giá các đêm **còn lại**, giữ nguyên giá đêm đã qua.

---

## R8. Trả phòng (check-out)

Điều kiện: booking đang `CheckedIn`.

1. Tổng hợp folio (xem R9), xuất hóa đơn
2. Đổi trạng thái phòng sang `Dirty`
3. Đổi trạng thái booking sang `CheckedOut`, ghi `checked_out_at`

Hệ thống **không** có task dọn phòng: lễ tân gọi buồng phòng ngoài đời. Dọn xong,
lễ tân đổi phòng về `Available` bằng `PATCH /rooms/{id}/status`.

---

## R9. Folio và hóa đơn

```
Tiền phòng     = tổng booking_night_rates của mọi booking_detail
Tiền dịch vụ   = tổng (unit_price × quantity) của booking_services
─────────────────────────────────────────────────────────────
Tạm tính       = tiền phòng + tiền dịch vụ
VAT            = tạm tính × VAT_RATE        (lấy từ settings, KHÔNG viết 0.08)
Tổng cộng      = tạm tính + VAT
Còn phải trả   = tổng cộng − đã thanh toán
```

Không có tiền cọc. Khách thanh toán khi ở/trả phòng.

Đơn giá dịch vụ cũng **chốt lúc ghi nhận**, không join sang bảng `services` khi
xuất hóa đơn.

Thanh toán cho phép nhiều lần, nhiều hình thức. Hoàn tiền lưu thành bản ghi
`payments` với số tiền **âm**. "Đã thanh toán" = tổng mọi `payments` (dương trừ âm).

Lễ tân kiêm luôn thu ngân: thu tiền, hoàn tiền, xem hóa đơn đều do lễ tân và Admin
làm.

---

## R10. Hủy booking và khách không đến

**Hủy (`/cancel`):**
- Chỉ hủy được khi booking đang `Confirmed`, bất cứ lúc nào (kể cả trước ngày đến).
- Bắt buộc ghi lý do (`cancel_reason`).
- Đổi trạng thái sang `Cancelled`, giữ nguyên bản ghi. Không `DELETE` khỏi DB — sẽ
  mất dữ liệu báo cáo.
- Phòng được nhả cho **mọi đêm** của booking (vì `Cancelled` không chiếm phòng).

**Khách không đến (`/no-show`):**
- Chỉ khi booking `Confirmed` và **hôm nay >= `check_in`** — chưa đến ngày đặt thì
  `BusinessError` code `TOO_EARLY_TO_NO_SHOW`.
- Đổi trạng thái sang `NoShow`, phòng được nhả cho mọi đêm.
- Khách đến muộn hơn ngày đặt thì lễ tân cứ check-in bình thường, không đánh
  no-show. Không có chuyện tự động hủy.

**Đã `CheckedIn` thì không hủy được.** Khách về sớm: dùng check-out (tính đủ số đêm
đã đặt). Không hỗ trợ trả phòng sớm tính lại tiền.

Muốn bớt vài đêm mà giữ phần còn lại: dùng sửa booking (R6), không phải hủy.

Không có tiền cọc nên hủy hay không đến đều không phát sinh hoàn tiền.

---

## R11. Phân quyền

Hệ thống chỉ có 2 vai trò:

| Vai trò | Được làm |
|---|---|
| `Admin` | Toàn quyền: quản lý user, loại phòng, phòng, danh mục dịch vụ, và mọi thao tác của lễ tân |
| `Receptionist` | Khách hàng, booking (đặt, sửa, hủy, check-in/out, đổi phòng), dịch vụ trong booking, thu/hoàn tiền, hóa đơn, báo cáo, xem danh mục, đổi trạng thái phòng |

Lễ tân kiêm luôn phần thu ngân/kế toán nên không có vai trò Kế toán riêng.
Không có vai trò Buồng phòng vì việc dọn phòng nằm ngoài hệ thống.

---

## R12. Báo cáo

```
Occupancy (%)  = số đêm-phòng đã bán / số đêm-phòng có thể bán × 100
ADR            = doanh thu phòng / số đêm-phòng đã bán
RevPAR         = doanh thu phòng / số đêm-phòng có thể bán
```

"Số đêm-phòng có thể bán" = số phòng không bảo trì × số ngày trong kỳ.

Doanh thu chỉ tính booking đã `CheckedIn` hoặc `CheckedOut`.

Quyền xem báo cáo: Admin và Lễ tân.
