import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_front_desk
from app.core.exceptions import BusinessError, NotFoundError
from app.core.response import ok
from app.db.session import get_db
from app.models import RoomType
from app.schemas.room import RoomOut
from app.services.availability_service import AvailabilityService

router = APIRouter(prefix="/availability", tags=["04. Tra cứu phòng trống"])


@router.get("", summary="Tra phòng trống theo loại phòng")
def search_availability(
        check_in: dt.date = Query(description="Ngày nhận phòng, dạng YYYY-MM-DD"),
        check_out: dt.date = Query(description="Ngày trả phòng, dạng YYYY-MM-DD"),
        guests: int = Query(default=1, ge=1,
                            description="Số khách; chỉ lọc loại phòng chứa đủ cả nhóm"),
        db: Session = Depends(get_db), _=Depends(require_front_desk)):
    return ok(AvailabilityService(db).search(check_in, check_out, guests))


@router.get("/rooms", summary="Danh sách phòng cụ thể còn trống của một loại")
def free_rooms(
        room_type_id: int = Query(description="Id loại phòng"),
        check_in: dt.date = Query(description="Ngày nhận phòng, dạng YYYY-MM-DD"),
        check_out: dt.date = Query(description="Ngày trả phòng, dạng YYYY-MM-DD"),
        db: Session = Depends(get_db), _=Depends(require_front_desk)):
    if check_out <= check_in:
        raise BusinessError("Ngày trả phòng phải sau ngày nhận phòng",
                            code="INVALID_DATE_RANGE")
    if not db.get(RoomType, room_type_id):
        raise NotFoundError("RoomType", room_type_id)
    rooms = AvailabilityService(db).free_rooms(room_type_id, check_in, check_out)
    return ok([RoomOut.model_validate(r) for r in rooms])
