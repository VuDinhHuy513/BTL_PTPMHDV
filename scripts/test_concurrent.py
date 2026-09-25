"""TODO — chứng minh cơ chế chống overbooking hoạt động.

Đây là thứ nên demo trực tiếp khi bảo vệ. Rất ít đồ án làm được phần này.

Cách chạy (database phải là MySQL/PostgreSQL thật, không phải SQLite):
    terminal 1:  uvicorn app.main:app --port 8000
    terminal 2:  python -m scripts.test_concurrent

Kịch bản:
    1. Đăng nhập lấy token (tài khoản lễ tân).
    2. Chọn MỘT phòng cụ thể còn trống và một khoảng ngày xa trong tương lai
       (chắc chắn chưa ai đặt).
    3. Dùng ThreadPoolExecutor bắn ~12 request POST /bookings ĐỒNG THỜI, tất cả
       cùng chọn ĐÚNG phòng đó (room_ids = [room_id]).
    4. Đếm kết quả.

Kết quả ĐÚNG:
    Thành công (201): 1
    Bị từ chối (409): 11    với code ROOM_NOT_AVAILABLE
    Số booking Confirmed giữ phòng đó trong khoảng ngày: 1

Nếu ra 2 hoặc nhiều hơn số 201 → khóa chưa hoạt động. Kiểm tra lại:
    - Việc kiểm tra phòng trống có nằm SAU lock_rooms (SELECT ... FOR UPDATE)
      không?
    - Có commit đúng lúc không, hay commit sớm làm nhả khóa quá sớm?
    - Có đang chạy SQLite không? SQLite bỏ qua FOR UPDATE nên không có khóa hàng.

Gợi ý: mỗi thread nên dùng một httpx.Client riêng, không dùng chung.
"""
