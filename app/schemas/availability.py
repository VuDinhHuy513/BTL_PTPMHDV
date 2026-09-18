import datetime as dt
from decimal import Decimal

from pydantic import BaseModel


class NightRateOut(BaseModel):
    date: dt.date
    price: Decimal


class AvailabilityOut(BaseModel):
    room_type_id: int
    name: str
    capacity: int
    available_count: int
    nightly_rates: list[NightRateOut]
    total_price: Decimal


class AvailabilitySearchOut(BaseModel):
    check_in: dt.date
    check_out: dt.date
    nights: int
    guests: int
    room_types: list[AvailabilityOut]
