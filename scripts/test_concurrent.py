"""TODO — chứng minh cơ chế chống overbooking hoạt động.

Đây là thứ nên demo trực tiếp khi bảo vệ. Rất ít đồ án làm được phần này.

Cách chạy:
    terminal 1:  uvicorn app.main:app --port 8000
    terminal 2:  python -m scripts.test_concurrent

Kịch bản:
    1. Đăng nhập lấy token.
    2. Chọn một khoảng ngày xa trong tương lai (chắc chắn chưa ai đặt).
    3. Đặt trước gần hết phòng để chỉ còn ĐÚNG 1 phòng trống.
    4. Dùng ThreadPoolExecutor bắn ~12 request ĐỒNG THỜI cùng đặt phòng đó.
    5. Đếm kết quả.

Kết quả ĐÚNG:
    Thành công (201): 1
    Bị từ chối (409): 11    với code ROOM_NOT_AVAILABLE
    Phòng trống còn lại: 0

Nếu ra 2 hoặc nhiều hơn số 201 → khóa chưa hoạt động. Kiểm tra lại:
    - Việc đếm phòng trống có nằm TRONG khối `with room_type_lock(...)` không?
    - Có commit đúng lúc không, hay commit sớm làm nhả khóa quá sớm?
    - Chạy PostgreSQL hay SQLite? SQLite chỉ khóa trong tiến trình.

Gợi ý: mỗi thread nên dùng một httpx.Client riêng, không dùng chung.
"""
