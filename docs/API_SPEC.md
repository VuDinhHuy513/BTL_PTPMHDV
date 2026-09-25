# Danh mục API cần làm

Prefix `/api/v1`. Đánh dấu ⬜ khi chưa làm, ✅ khi đã test xong.

Quy ước chung: xem `docs/CONVENTIONS.md` mục 7 và 8.

Hệ thống chỉ có 2 vai trò: **Admin** (toàn quyền) và **Lễ tân** (mọi thao tác nghiệp
vụ hằng ngày, kiêm thu ngân). Cột "Quyền" ghi "Nhân viên" nghĩa là Admin + Lễ tân.

| Trạng thái | Method | Endpoint | Quyền |
|---|---|---|---|
| | | **01. Xác thực** | |
| ⬜ | POST | `/auth/login` | Public |
| ⬜ | POST | `/auth/refresh` | Public |
| ⬜ | POST | `/auth/logout` | Đã đăng nhập |
| ⬜ | GET | `/auth/me` | Đã đăng nhập |
| | | **02. Loại phòng** | |
| ✅ | GET | `/room-types` | Mọi vai trò |
| ✅ | GET | `/room-types/{id}` | Mọi vai trò |
| ✅ | POST | `/room-types` | Admin |
| ✅ | PUT | `/room-types/{id}` | Admin |
| ✅ | DELETE | `/room-types/{id}` | Admin |
| | | **03. Phòng** | |
| ⬜ | GET | `/rooms?floor=&room_type_id=&status=` | Mọi vai trò |
| ⬜ | GET | `/rooms/schedule?from=&to=` (sơ đồ phòng theo ngày) | Nhân viên |
| ⬜ | GET | `/rooms/{id}` | Mọi vai trò |
| ⬜ | POST | `/rooms` | Admin |
| ⬜ | PUT | `/rooms/{id}` | Admin |
| ⬜ | PATCH | `/rooms/{id}/status` | Nhân viên |
| ⬜ | DELETE | `/rooms/{id}` | Admin |
| | | **04. Tra cứu phòng trống** ⭐ | |
| ⬜ | GET | `/availability?check_in=&check_out=&guests=` | Nhân viên |
| ⬜ | GET | `/availability/rooms?room_type_id=&check_in=&check_out=` | Nhân viên |
| | | **05. Khách hàng** | |
| ⬜ | GET | `/customers?search=&page=&limit=` | Nhân viên |
| ⬜ | GET | `/customers/{id}` | Nhân viên |
| ⬜ | GET | `/customers/{id}/bookings` | Nhân viên |
| ⬜ | POST | `/customers` | Nhân viên |
| ⬜ | PUT | `/customers/{id}` | Nhân viên |
| | | **06. Đặt phòng** ⭐ | |
| ⬜ | GET | `/bookings?status=&from=&to=&customer_id=&page=` | Nhân viên |
| ⬜ | GET | `/bookings/{id}` | Nhân viên |
| ⬜ | GET | `/bookings/code/{code}` | Nhân viên |
| ⬜ | POST | `/bookings` (body có `room_ids`) | Nhân viên |
| ⬜ | PUT | `/bookings/{id}` | Nhân viên |
| ⬜ | DELETE | `/bookings/{id}` | Nhân viên |
| ⬜ | POST | `/bookings/{id}/cancel` | Nhân viên |
| ⬜ | POST | `/bookings/{id}/no-show` | Nhân viên |
| | | **07. Nhận / trả phòng** ⭐ | |
| ⬜ | POST | `/bookings/walk-in` | Nhân viên |
| ⬜ | POST | `/bookings/{id}/check-in` | Nhân viên |
| ⬜ | POST | `/bookings/{id}/change-room` | Nhân viên |
| ⬜ | POST | `/bookings/{id}/check-out` | Nhân viên |
| | | **08. Dịch vụ** | |
| ⬜ | GET | `/services` | Mọi vai trò |
| ⬜ | POST | `/services` | Admin |
| ⬜ | PUT | `/services/{id}` | Admin |
| ⬜ | GET | `/bookings/{id}/services` | Nhân viên |
| ⬜ | POST | `/bookings/{id}/services` | Nhân viên |
| ⬜ | DELETE | `/bookings/{id}/services/{line_id}` | Nhân viên |
| | | **09. Thanh toán & hóa đơn** ⭐ | |
| ⬜ | GET | `/bookings/{id}/folio` | Nhân viên |
| ⬜ | GET | `/bookings/{id}/payments` | Nhân viên |
| ⬜ | POST | `/bookings/{id}/payments` | Nhân viên |
| ⬜ | POST | `/payments/{id}/refund` | Nhân viên |
| ⬜ | GET | `/invoices?from=&to=` | Nhân viên |
| ⬜ | GET | `/invoices/{id}` | Nhân viên |
| | | **10. Báo cáo** | |
| ⬜ | GET | `/reports/occupancy?from=&to=` | Nhân viên |
| ⬜ | GET | `/reports/revenue?from=&to=&groupBy=` | Nhân viên |
| ⬜ | GET | `/reports/adr-revpar?from=&to=` | Nhân viên |
| ⬜ | GET | `/reports/arrivals?date=` | Nhân viên |
| ⬜ | GET | `/reports/departures?date=` | Nhân viên |
| ⬜ | GET | `/reports/dashboard` | Nhân viên |
| | | **11. Quản trị** | |
| ⬜ | GET | `/users` | Admin |
| ⬜ | POST | `/users` | Admin |
| ⬜ | PUT | `/users/{id}` | Admin |
| ⬜ | PATCH | `/users/{id}/status` | Admin |

**Tổng: 57 endpoint.**

Nếu thiếu thời gian, cắt theo thứ tự: `/reports/adr-revpar` → `/bookings/{id}/change-room`
→ `/rooms/schedule`. Không cắt nhóm 04, 06, 07, 09 — đó là xương sống.
