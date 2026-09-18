"""Điểm khởi động ứng dụng: đăng ký router, CORS, exception handler, Swagger."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException

log = logging.getLogger("hotel_pms")

DESCRIPTION = """
API quản lý khách sạn (Hotel PMS) — đồ án môn học.

**Luồng nghiệp vụ chính:**
`GET /availability` → `POST /bookings` → `POST /bookings/{id}/check-in`
→ `POST /bookings/{id}/services` → `GET /bookings/{id}/folio`
→ `POST /bookings/{id}/check-out`

**Cách dùng Swagger:** gọi `POST /auth/login` với `admin / admin123`,
copy `access_token`, bấm nút **Authorize** ở góc trên bên phải rồi dán vào.
"""

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------- exception handler
# Mọi lỗi đều trả về cùng một format, Service chỉ cần raise.
def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"success": False, "error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


@app.exception_handler(AppException)
def handle_app_exception(request: Request, exc: AppException):
    return _error(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(x) for x in e["loc"][1:]),
                "issue": e["msg"]} for e in exc.errors()]
    return _error(422, "VALIDATION_ERROR", "Dữ liệu đầu vào không hợp lệ", details)


@app.exception_handler(IntegrityError)
def handle_integrity_error(request: Request, exc: IntegrityError):
    log.warning("IntegrityError: %s", exc)
    return _error(409, "DB_CONSTRAINT_VIOLATED",
                  "Thao tác vi phạm ràng buộc dữ liệu (trùng khóa hoặc khóa ngoại)")


@app.exception_handler(Exception)
def handle_unexpected(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return _error(500, "INTERNAL_ERROR", "Lỗi hệ thống, vui lòng thử lại")


# ------------------------------------------------------------------- routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["00. Hệ thống"], summary="Kiểm tra API còn sống")
def health():
    return {"success": True, "data": {"status": "ok"}}
