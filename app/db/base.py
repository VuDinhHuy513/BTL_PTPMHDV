"""Base class cho mọi model + import gom để Alembic thấy đủ bảng."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Alembic autogenerate chỉ thấy bảng nào được import ở đây.
# TODO: mở comment dần khi viết xong từng model.
from app.models import room  # noqa: E402,F401

# from app.models import booking, customer, payment, service, user  # noqa: E402,F401
