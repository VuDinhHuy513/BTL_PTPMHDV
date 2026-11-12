"""Engine, session factory và dependency get_db."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# READ COMMITTED: mỗi câu SELECT thấy dữ liệu mới nhất đã commit. Cần cho chống
# overbooking (R5): MySQL mặc định REPEATABLE READ chụp snapshot ở lần đọc đầu
# tiên của transaction (vd: tra user lúc xác thực), nên sau khi chờ khóa phòng
# xong, request đến sau sẽ KHÔNG thấy booking mà request trước vừa commit.
# SQLite không hỗ trợ mức này nên bỏ qua.
engine_kwargs = {} if is_sqlite else {"isolation_level": "READ COMMITTED"}

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
    **engine_kwargs,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
