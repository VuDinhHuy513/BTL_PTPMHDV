"""TODO — báo cáo. Công thức ở docs/BUSINESS_RULES.md mục R12.

    GET /reports/occupancy?from=&to=
    GET /reports/revenue?from=&to=&groupBy=day|roomType|service
    GET /reports/adr-revpar?from=&to=
    GET /reports/arrivals?date=
    GET /reports/departures?date=
    GET /reports/dashboard
    GET /audit-logs?entity=&from=&to=

Giới hạn khoảng báo cáo tối đa 1 năm để tránh query quét cả bảng.
"""
from fastapi import APIRouter

router = APIRouter(tags=["11. Báo cáo"])
