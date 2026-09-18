"""Khóa bi quan để chống overbooking. Xem docs/BUSINESS_RULES.md mục R5.

╔══════════════════════════════════════════════════════════════════════════╗
║ VẤN ĐỀ                                                                   ║
║                                                                          ║
║ Còn đúng 1 phòng. Hai request đến cùng lúc:                              ║
║                                                                          ║
║   Request A                      Request B                               ║
║   ───────────                    ───────────                             ║
║   đếm phòng trống → 1                                                    ║
║                                  đếm phòng trống → 1   ← vẫn thấy 1!    ║
║   1 >= 1, OK, ghi booking                                                ║
║                                  1 >= 1, OK, ghi booking                 ║
║                                                                          ║
║   → 2 booking cho 1 phòng. Khách đến khách sạn mới biết.                 ║
║                                                                          ║
║ Kiểm tra rồi mới ghi (check-then-act) KHÔNG an toàn khi có đồng thời.    ║
╠══════════════════════════════════════════════════════════════════════════╣
║ GIẢI PHÁP                                                                ║
║                                                                          ║
║ Giữ khóa theo room_type_id trong SUỐT transaction. Request B phải đợi    ║
║ A commit xong mới được đếm, lúc đó nó thấy 0 phòng và bị từ chối.        ║
║                                                                          ║
║   with room_type_lock(db, room_type_id):                                 ║
║       free = count_available(...)   ← đếm SAU KHI đã giữ khóa            ║
║       if free < quantity: raise BusinessError(...)                       ║
║       db.add(booking)                                                    ║
║   db.commit()   ← khóa tự nhả ở đây                                      ║
╚══════════════════════════════════════════════════════════════════════════╝

TODO — viết hàm room_type_lock(db, room_type_id) dạng context manager.

PostgreSQL (khuyến nghị):
    SELECT pg_advisory_xact_lock(:namespace, :key)
    Khóa tự nhả khi COMMIT/ROLLBACK, không cần nhả tay.
    Dùng namespace là một số cố định để không đụng key của phần khác.

MySQL:
    SELECT GET_LOCK(:name, :timeout)   rồi   SELECT RELEASE_LOCK(:name)
    Khóa KHÔNG tự nhả theo transaction, phải nhả trong finally.

SQLite / môi trường dev:
    Fallback bằng threading.Lock trong tiến trình.
    Chỉ đúng khi chạy 1 worker — ghi rõ hạn chế này vào báo cáo.

Gợi ý khung:

    from contextlib import contextmanager

    @contextmanager
    def room_type_lock(db: Session, room_type_id: int):
        if settings.is_postgres:
            db.execute(text("SELECT pg_advisory_xact_lock(:ns, :key)"),
                       {"ns": LOCK_NAMESPACE, "key": room_type_id})
            yield
        else:
            lock = _get_local_lock(room_type_id)
            lock.acquire()
            try:
                yield
            finally:
                lock.release()

LƯU Ý khi đặt nhiều loại phòng cùng lúc: khóa theo thứ tự room_type_id TĂNG DẦN.
Nếu request A khóa theo thứ tự 1→2 còn B khóa 2→1 thì hai bên chờ nhau vĩnh viễn
(deadlock). Dùng contextlib.ExitStack để giữ nhiều khóa cùng lúc.
"""
