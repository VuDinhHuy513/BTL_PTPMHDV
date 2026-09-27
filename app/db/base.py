"""Base class cho mọi model + import gom để Alembic thấy đủ bảng."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Alembic autogenerate chỉ thấy bảng nào được import ở đây.
from app.models import (booking, customer, payment, room, service,  # noqa: E402,F401
                        user)
