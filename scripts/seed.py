"""TODO — tạo dữ liệu mẫu.  Chạy: python -m scripts.seed

Vì sao cần seed? Báo cáo occupancy/doanh thu mà DB rỗng thì demo ra toàn số 0.
Giảng viên nhìn là biết chưa chạy thật.

Nên tạo:
    - 4 tài khoản, mỗi vai trò một cái (nhớ hash mật khẩu)
    - 5 loại phòng, ~48 phòng, trong đó 2 phòng để OutOfOrder
      ↳ để kiểm chứng phòng bảo trì bị loại khỏi kết quả tra phòng trống
    - 7 dịch vụ
    - Giá cuối tuần +30% (thứ Sáu, Bảy, Chủ Nhật)
    - ~80 khách hàng
    - ~200 booking TRẢI ĐỀU từ 60 ngày trước đến 90 ngày sau,
      đủ mọi trạng thái: CheckedOut (quá khứ), CheckedIn (đang ở),
      Confirmed/Pending/Cancelled (tương lai)
    - Dịch vụ + thanh toán cho các booking đã/đang ở

⚠ Đặt random.seed(42) ở đầu file để chạy lại ra cùng dữ liệu, dễ debug.

⚠ Khi sinh booking ngẫu nhiên, phải tự theo dõi phòng nào đã bị chiếm khoảng
  ngày nào — nếu không seed sẽ tạo ra chính cái overbooking mà bạn đang
  cố chống, rồi test phòng trống sẽ ra số vô lý.

Khung gợi ý:

    busy: dict[int, list[tuple[date, date]]] = {r.id: [] for r in rooms}

    def pick_room(rt_id, ci, co):
        for r in rooms_of_type(rt_id):
            if all(not (ci < e and co > s) for s, e in busy[r.id]):
                return r
        return None
"""
