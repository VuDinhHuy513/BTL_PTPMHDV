"""Khóa bi quan để chống overbooking. Xem docs/BUSINESS_RULES.md mục R5.

╔══════════════════════════════════════════════════════════════════════════╗
║ VẤN ĐỀ                                                                   ║
║                                                                          ║
║ Hai lễ tân cùng lúc nhận hai cuộc gọi, cùng chọn phòng 101:              ║
║                                                                          ║
║   Request A                      Request B                               ║
║   ───────────                    ───────────                             ║
║   kiểm tra 101 trống → có                                                ║
║                                  kiểm tra 101 trống → có  ← vẫn thấy!    ║
║   ghi booking cho 101                                                    ║
║                                  ghi booking cho 101                     ║
║                                                                          ║
║   → 2 booking cho 1 phòng. Khách đến khách sạn mới biết.                 ║
║                                                                          ║
║ Kiểm tra rồi mới ghi (check-then-act) KHÔNG an toàn khi có đồng thời.    ║
╠══════════════════════════════════════════════════════════════════════════╣
║ GIẢI PHÁP                                                                ║
║                                                                          ║
║ Khóa CHÍNH các dòng phòng trong bảng rooms suốt transaction. Request B   ║
║ phải đợi A commit xong mới được kiểm tra, lúc đó nó thấy 101 đã bận     ║
║ và bị từ chối.                                                           ║
║                                                                          ║
║   lock_rooms(db, room_ids)      ← SELECT ... FOR UPDATE                  ║
║   kiểm tra phòng còn trống      ← SAU KHI đã khóa                        ║
║   db.add(booking)                                                        ║
║   db.commit()                   ← khóa tự nhả ở đây                      ║
╚══════════════════════════════════════════════════════════════════════════╝

MySQL (InnoDB) và PostgreSQL đều hỗ trợ SELECT ... FOR UPDATE: khóa hàng tự
nhả khi COMMIT/ROLLBACK, không cần nhả tay. Không cần GET_LOCK hay advisory lock.

SQLite (dùng khi chạy test tự động): bỏ qua FOR UPDATE, không có khóa hàng.
Test tự động chạy tuần tự nên vẫn đúng; việc chứng minh khóa hoạt động phải
làm bằng scripts/test_concurrent.py trên MySQL thật. Ghi rõ điều này vào báo cáo.

LƯU Ý: luôn khóa theo thứ tự room_id TĂNG DẦN (ORDER BY id ở trên). Nếu request
A khóa 101→102 còn B khóa 102→101 thì hai bên chờ nhau vĩnh viễn (deadlock).

Giới hạn cần nêu trong báo cáo: MySQL không có ràng buộc "cấm hai khoảng ngày
chồng nhau trên cùng một phòng" ở mức database, nên chống trùng dựa hoàn toàn
vào khóa này ở tầng code.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.room import Room


def lock_rooms(db: Session, room_ids: list[int]) -> None:
    """Khóa các dòng phòng bằng SELECT ... FOR UPDATE cho tới khi commit/rollback.

    Gọi TRƯỚC khi kiểm tra phòng trống. Luôn khóa theo room_id tăng dần.
    """
    ids = sorted(set(room_ids))
    db.execute(select(Room.id).where(Room.id.in_(ids))
               .order_by(Room.id).with_for_update())
