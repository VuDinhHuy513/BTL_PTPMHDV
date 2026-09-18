"""Gom model để import cho gọn: `from app.models import Booking, Room`

TODO: mở comment dần khi viết xong từng model.
"""
from app.models.enums import (BLOCKING_STATUSES, BookingStatus,
                              HousekeepingStatus, PaymentMethod, Role,
                              RoomStatus)
from app.models.room import Room, RoomType

# from app.models.audit import AuditLog
# from app.models.booking import Booking, BookingDetail, BookingNightRate
# from app.models.customer import Customer
# from app.models.housekeeping import HousekeepingTask
# from app.models.payment import Invoice, Payment
# from app.models.rate import RatePrice
# from app.models.service import BookingService, Service
# from app.models.user import User

__all__ = [
    "Role", "RoomStatus", "BookingStatus", "PaymentMethod",
    "HousekeepingStatus", "BLOCKING_STATUSES", "Room", "RoomType",
]
