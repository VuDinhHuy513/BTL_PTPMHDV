"""TODO — báo cáo. Công thức ở docs/BUSINESS_RULES.md mục R12.
Quyền: require_front_desk (Admin + Lễ tân).

    GET /reports/occupancy?from=&to=
    GET /reports/revenue?from=&to=&groupBy=day|roomType|service
    GET /reports/adr-revpar?from=&to=
    GET /reports/arrivals?date=
    GET /reports/departures?date=
    GET /reports/dashboard

Giới hạn khoảng báo cáo tối đa 1 năm để tránh query quét cả bảng.
"""
from fastapi import APIRouter

router = APIRouter(tags=["10. Báo cáo"])
