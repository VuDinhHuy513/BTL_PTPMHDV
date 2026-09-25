"""Gom toàn bộ router. Thứ tự khai báo quyết định thứ tự hiện trên Swagger.

TODO: bỏ comment dần khi viết xong từng nhóm endpoint.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import room_types

api_router = APIRouter()

api_router.include_router(room_types.router)

# api_router.include_router(auth.router)
# api_router.include_router(rooms.router)
# api_router.include_router(availability.router)
# api_router.include_router(customers.router)
# api_router.include_router(bookings.router)
# api_router.include_router(services.router)
# api_router.include_router(payments.router)
# api_router.include_router(reports.router)
# api_router.include_router(users.router)
