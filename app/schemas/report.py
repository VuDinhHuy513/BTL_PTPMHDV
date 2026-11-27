"""DTO cho báo cáo quản trị. Xem R12.

Mọi số tiền ở đây là doanh thu CHƯA gồm VAT: VAT là tiền thuế thu hộ nhà nước,
không phải doanh thu của khách sạn.
"""
import datetime as dt
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel

from app.models.enums import BookingStatus


class RevenueGroupBy(str, Enum):
    """Giá trị hợp lệ của ?groupBy= — enum để FastAPI tự trả 422 khi gõ sai."""
    DAY = "day"
    ROOM_TYPE = "roomType"
    SERVICE = "service"


class OccupancyRow(BaseModel):
    date: dt.date
    available_rooms: int            # phòng bán được (không bảo trì)
    sold_rooms: int                 # đêm-phòng đã bán trong ngày
    occupancy_pct: Decimal


class OccupancyOut(BaseModel):
    from_date: dt.date
    to_date: dt.date
    rows: list[OccupancyRow]
    available_room_nights: int
    sold_room_nights: int
    occupancy_pct: Decimal          # của cả kỳ, không phải trung bình cộng các ngày


class RevenueRow(BaseModel):
    key: str                        # ngày (YYYY-MM-DD) / id loại phòng / id dịch vụ
    label: str                      # chữ để hiển thị
    quantity: int                   # số đêm-phòng (day, roomType) hoặc số đơn vị dịch vụ
    room_revenue: Decimal
    service_revenue: Decimal
    total: Decimal


class RevenueOut(BaseModel):
    from_date: dt.date
    to_date: dt.date
    group_by: RevenueGroupBy
    rows: list[RevenueRow]
    room_revenue: Decimal
    service_revenue: Decimal
    total: Decimal


class AdrRevparOut(BaseModel):
    from_date: dt.date
    to_date: dt.date
    days: int
    available_room_nights: int
    sold_room_nights: int
    room_revenue: Decimal
    occupancy_pct: Decimal
    adr: Decimal                    # giá bán bình quân một đêm-phòng
    revpar: Decimal                 # doanh thu bình quân trên MỖI phòng có thể bán


class ArrivalDepartureRow(BaseModel):
    booking_id: int
    code: str
    customer_name: str
    customer_phone: str
    room_numbers: list[str]
    check_in: dt.date
    check_out: dt.date
    guests: int
    status: BookingStatus


class DashboardOut(BaseModel):
    date: dt.date
    total_rooms: int                # mọi phòng, kể cả đang bảo trì
    available_rooms: int            # đang sạch, sẵn sàng nhận khách
    occupied_rooms: int
    dirty_rooms: int
    out_of_order_rooms: int
    in_house_bookings: int          # booking đang CheckedIn
    arrivals_pending: int           # hôm nay phải đến mà chưa check-in
    departures_pending: int         # hôm nay phải đi mà chưa check-out
    occupancy_pct: Decimal          # đêm nay
    room_revenue_today: Decimal
    service_revenue_today: Decimal
