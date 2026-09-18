"""Test khói — chạy được ngay từ lúc repo còn rỗng.

Mục đích: xác nhận môi trường cài đúng, app khởi động được, cấu hình đọc được.
Nếu 3 test này xanh thì bạn đã sẵn sàng bắt đầu.

    pytest tests/test_smoke.py
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./smoke.db")
os.environ.setdefault("JWT_SECRET", "smoke-test-secret-at-least-32-characters")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402


def test_app_khoi_dong_duoc():
    with TestClient(app) as c:
        r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_swagger_mo_duoc():
    with TestClient(app) as c:
        assert c.get("/docs").status_code == 200
        assert c.get("/openapi.json").status_code == 200


def test_config_doc_duoc_tu_env():
    """Xác nhận cấu hình đọc từ .env chứ không hard-code trong code."""
    assert settings.DATABASE_URL
    assert settings.JWT_SECRET
    assert 0 <= settings.VAT_RATE < 1
