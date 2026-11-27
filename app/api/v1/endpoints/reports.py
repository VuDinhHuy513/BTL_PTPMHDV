"""Báo cáo (nhóm 10). Công thức ở docs/BUSINESS_RULES.md mục R12.
Quyền: require_front_desk (Admin + Lễ tân).

    GET /reports/occupancy?from=&to=
    GET /reports/revenue?from=&to=&groupBy=day|roomType|service
    GET /reports/adr-revpar?from=&to=
    GET /reports/arrivals?date=          bỏ trống = hôm nay
    GET /reports/departures?date=        bỏ trống = hôm nay
    GET /reports/dashboard

Kỳ báo cáo [from, to] tính CẢ ngày to, tối đa 1 năm mỗi lần.
"""
import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_front_desk
from app.core.response import ok
from app.db.session import get_db
from app.schemas.report import RevenueGroupBy
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["10. Báo cáo"])

FROM = Query(alias="from", description="Ngày đầu kỳ, YYYY-MM-DD")
TO = Query(alias="to", description="Ngày cuối kỳ (tính cả ngày này), YYYY-MM-DD")


@router.get("/occupancy", summary="Công suất phòng từng ngày")
def occupancy(from_date: dt.date = FROM, to_date: dt.date = TO,
              db: Session = Depends(get_db), _=Depends(require_front_desk)):
    return ok(ReportService(db).occupancy(from_date, to_date))


@router.get("/revenue", summary="Doanh thu theo ngày / loại phòng / dịch vụ (chưa VAT)")
def revenue(from_date: dt.date = FROM, to_date: dt.date = TO,
            group_by: RevenueGroupBy = Query(default=RevenueGroupBy.DAY, alias="groupBy"),
            db: Session = Depends(get_db), _=Depends(require_front_desk)):
    return ok(ReportService(db).revenue(from_date, to_date, group_by))


@router.get("/adr-revpar", summary="ADR, RevPAR và công suất của cả kỳ")
def adr_revpar(from_date: dt.date = FROM, to_date: dt.date = TO,
               db: Session = Depends(get_db), _=Depends(require_front_desk)):
    return ok(ReportService(db).adr_revpar(from_date, to_date))


@router.get("/arrivals", summary="Khách đến trong ngày")
def arrivals(date: dt.date | None = Query(default=None, description="Bỏ trống = hôm nay"),
             db: Session = Depends(get_db), _=Depends(require_front_desk)):
    return ok(ReportService(db).arrivals(date or dt.date.today()))


@router.get("/departures", summary="Khách đi trong ngày")
def departures(date: dt.date | None = Query(default=None, description="Bỏ trống = hôm nay"),
               db: Session = Depends(get_db), _=Depends(require_front_desk)):
    return ok(ReportService(db).departures(date or dt.date.today()))


@router.get("/dashboard", summary="Tổng quan hôm nay")
def dashboard(db: Session = Depends(get_db), _=Depends(require_front_desk)):
    return ok(ReportService(db).dashboard())
