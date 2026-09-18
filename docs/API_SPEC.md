# Danh mục API cần làm

Prefix `/api/v1`. Đánh dấu ⬜ khi chưa làm, ✅ khi đã test xong.

Quy ước chung: xem `docs/CONVENTIONS.md` mục 7 và 8.

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
| ⬜ | GET | `/rooms/{id}` | Mọi vai trò |
| ⬜ | POST | `/rooms` | Admin |
| ⬜ | PUT | `/rooms/{id}` | Admin |
| ⬜ | PATCH | `/rooms/{id}/status` | Admin, Buồng phòng |
| ⬜ | DELETE | `/rooms/{id}` | Admin |
| | | **04. Giá phòng** | |
| ⬜ | GET | `/rates?room_type_id=&from=&to=` | Admin, Lễ tân |
| ⬜ | POST | `/rates` | Admin |
| ⬜ | POST | `/rates/bulk` | Admin |
| ⬜ | DELETE | `/rates/{id}` | Admin |
| | | **05. Tra cứu phòng trống** ⭐ | |
| ⬜ | GET | `/availability?check_in=&check_out=&guests=` | Mọi vai trò |
| ⬜ | GET | `/availability/rooms?room_type_id=&check_in=&check_out=` | Lễ tân |
| | | **06. Khách hàng** | |
| ⬜ | GET | `/customers?search=&page=&limit=` | Lễ tân |
| ⬜ | GET | `/customers/{id}` | Lễ tân |
| ⬜ | GET | `/customers/{id}/bookings` | Lễ tân |
| ⬜ | POST | `/customers` | Lễ tân |
| ⬜ | PUT | `/customers/{id}` | Lễ tân |
| | | **07. Đặt phòng** ⭐ | |
| ⬜ | GET | `/bookings?status=&from=&to=&customer_id=&page=` | Lễ tân |
| ⬜ | GET | `/bookings/{id}` | Lễ tân |
| ⬜ | GET | `/bookings/code/{code}` | Lễ tân |
| ⬜ | POST | `/bookings` | Lễ tân |
| ⬜ | PUT | `/bookings/{id}` | Lễ tân |
| ⬜ | DELETE | `/bookings/{id}` | Lễ tân |
| ⬜ | POST | `/bookings/{id}/confirm` | Lễ tân |
| ⬜ | POST | `/bookings/{id}/cancel` | Lễ tân |
| ⬜ | POST | `/bookings/{id}/no-show` | Lễ tân |
| | | **08. Nhận / trả phòng** ⭐ | |
| ⬜ | POST | `/bookings/walk-in` | Lễ tân |
| ⬜ | POST | `/bookings/{id}/check-in` | Lễ tân |
| ⬜ | POST | `/bookings/{id}/change-room` | Lễ tân |
| ⬜ | POST | `/bookings/{id}/check-out` | Lễ tân |
| | | **09. Dịch vụ** | |
| ⬜ | GET | `/services` | Mọi vai trò |
| ⬜ | POST | `/services` | Admin |
| ⬜ | PUT | `/services/{id}` | Admin |
| ⬜ | GET | `/bookings/{id}/services` | Lễ tân |
| ⬜ | POST | `/bookings/{id}/services` | Lễ tân |
| ⬜ | DELETE | `/bookings/{id}/services/{line_id}` | Lễ tân |
| | | **10. Thanh toán & hóa đơn** | |
| ⬜ | GET | `/bookings/{id}/folio` | Lễ tân, Kế toán |
| ⬜ | GET | `/bookings/{id}/payments` | Lễ tân, Kế toán |
| ⬜ | POST | `/bookings/{id}/payments` | Lễ tân |
| ⬜ | POST | `/payments/{id}/refund` | Admin, Kế toán |
| ⬜ | GET | `/invoices?from=&to=` | Kế toán |
| ⬜ | GET | `/invoices/{id}` | Kế toán |
| | | **11. Buồng phòng** | |
| ⬜ | GET | `/housekeeping/tasks?date=&status=&assignee_id=` | Buồng phòng |
| ⬜ | POST | `/housekeeping/tasks` | Admin, Buồng phòng |
| ⬜ | PATCH | `/housekeeping/tasks/{id}` | Buồng phòng |
| ⬜ | GET | `/housekeeping/room-status` | Buồng phòng |
| | | **12. Báo cáo** | |
| ⬜ | GET | `/reports/occupancy?from=&to=` | Admin, Kế toán |
| ⬜ | GET | `/reports/revenue?from=&to=&groupBy=` | Admin, Kế toán |
| ⬜ | GET | `/reports/adr-revpar?from=&to=` | Admin, Kế toán |
| ⬜ | GET | `/reports/arrivals?date=` | Lễ tân |
| ⬜ | GET | `/reports/departures?date=` | Lễ tân |
| ⬜ | GET | `/reports/dashboard` | Lễ tân |
| | | **13. Quản trị** | |
| ⬜ | GET | `/users` | Admin |
| ⬜ | POST | `/users` | Admin |
| ⬜ | PUT | `/users/{id}` | Admin |
| ⬜ | PATCH | `/users/{id}/status` | Admin |
| ⬜ | GET | `/audit-logs?entity=&from=&to=` | Admin |

**Tổng: 64 endpoint.**

Nếu thiếu thời gian, cắt theo thứ tự: `/audit-logs` → nhóm Buồng phòng →
`/reports/adr-revpar`. Không cắt nhóm 05, 07, 08, 10 — đó là xương sống.
