"""Format response thống nhất cho toàn bộ API."""
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PageMeta(BaseModel):
    page: int
    limit: int
    total: int


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    meta: PageMeta | None = None


def ok(data, meta: PageMeta | None = None) -> dict:
    return {"success": True, "data": data, "meta": meta}
