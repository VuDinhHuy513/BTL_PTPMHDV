from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import RoomStatus
from app.schemas.common import ORMBase


class RoomTypeIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    capacity: int = Field(ge=1, le=10)
    base_price: Decimal = Field(gt=0)
    description: str | None = Field(default=None, max_length=500)


class RoomTypeOut(ORMBase):
    id: int
    name: str
    capacity: int
    base_price: Decimal
    description: str | None = None


class RoomIn(BaseModel):
    room_number: str = Field(min_length=1, max_length=20)
    floor: int = Field(ge=0, le=100)
    room_type_id: int
    status: RoomStatus = RoomStatus.AVAILABLE


class RoomOut(ORMBase):
    id: int
    room_number: str
    floor: int
    room_type_id: int
    status: RoomStatus


class RoomStatusIn(BaseModel):
    status: RoomStatus
