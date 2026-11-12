from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class CustomerIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    # Số điện thoại dùng để nhận ra khách cũ (R5): chỉ chữ số, có thể có dấu + đầu
    phone: str = Field(pattern=r"^\+?\d{8,15}$")
    email: str | None = Field(default=None, max_length=100)
    id_card_number: str | None = Field(default=None, max_length=20)
    nationality: str | None = Field(default=None, max_length=50)


class CustomerOut(ORMBase):
    id: int
    full_name: str
    phone: str
    email: str | None = None
    id_card_number: str | None = None
    nationality: str | None = None
