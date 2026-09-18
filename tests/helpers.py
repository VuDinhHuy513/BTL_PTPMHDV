"""Tiện ích cho test: bỏ qua file test khi model chưa viết xong.

Nhờ cái này mà `pytest` chạy được ngay từ lúc repo còn rỗng — test nào chưa
đủ điều kiện thì hiện SKIPPED kèm lý do, thay vì cả bộ test đổ vỡ.
"""
import pytest


def require_models(*names: str) -> None:
    """Bỏ qua cả file test nếu model chưa được khai báo trong app/models/__init__.py"""
    try:
        import app.models as m
    except Exception as exc:                      # noqa: BLE001
        pytest.skip(f"Chưa import được app.models: {exc}", allow_module_level=True)

    missing = [n for n in names if not hasattr(m, n)]
    if missing:
        pytest.skip(
            "Chưa viết xong model: " + ", ".join(missing)
            + ". Viết model rồi bỏ comment trong app/models/__init__.py.",
            allow_module_level=True)
