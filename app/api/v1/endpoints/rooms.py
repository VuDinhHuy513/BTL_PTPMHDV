from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_admin, require_any, require_front_desk
from app.core.exceptions import BusinessError, NotFoundError
from app.core.response import ok
from app.db.session import get_db
from app.models import BookingDetail, Room, RoomStatus
from app.schemas.room import RoomIn, RoomOut, RoomStatusIn

router = APIRouter(prefix="/rooms", tags=["03. Phòng"])


@router.get("", summary="Danh sách phòng")
def list_rooms(floor: int | None = Query(default=None),
               room_type_id: int | None = Query(default=None),
               status: RoomStatus | None = Query(default=None),
               db: Session = Depends(get_db), _=Depends(require_any)):
    stmt = select(Room)
    if floor is not None:
        stmt = stmt.where(Room.floor == floor)
    if room_type_id is not None:
        stmt = stmt.where(Room.room_type_id == room_type_id)
    if status is not None:
        stmt = stmt.where(Room.status == status)
    rows = db.scalars(stmt.order_by(Room.floor, Room.room_number)).all()
    return ok([RoomOut.model_validate(r) for r in rows])


@router.get("/{room_id}", summary="Chi tiết phòng")
def get_room(room_id: int, db: Session = Depends(get_db), _=Depends(require_any)):
    room = db.get(Room, room_id)
    if not room:
        raise NotFoundError("Room", room_id)
    return ok(RoomOut.model_validate(room))


@router.post("", status_code=201, summary="Thêm phòng")
def create_room(dto: RoomIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.scalar(select(Room.id).where(Room.room_number == dto.room_number)):
        raise BusinessError("Số phòng đã tồn tại", code="DUPLICATE_ROOM_NUMBER")
    room = Room(**dto.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return ok(RoomOut.model_validate(room))


@router.put("/{room_id}", summary="Sửa phòng")
def update_room(room_id: int, dto: RoomIn, db: Session = Depends(get_db),
                _=Depends(require_admin)):
    room = db.get(Room, room_id)
    if not room:
        raise NotFoundError("Room", room_id)
    for k, v in dto.model_dump().items():
        setattr(room, k, v)
    db.commit()
    db.refresh(room)
    return ok(RoomOut.model_validate(room))


@router.patch("/{room_id}/status", summary="Đổi trạng thái phòng")
def update_room_status(room_id: int, dto: RoomStatusIn, db: Session = Depends(get_db),
                       _=Depends(require_front_desk)):
    room = db.get(Room, room_id)
    if not room:
        raise NotFoundError("Room", room_id)
    room.status = dto.status
    db.commit()
    db.refresh(room)
    return ok(RoomOut.model_validate(room))


@router.delete("/{room_id}", summary="Xóa phòng")
def delete_room(room_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    room = db.get(Room, room_id)
    if not room:
        raise NotFoundError("Room", room_id)
    if db.scalar(select(BookingDetail.id).where(BookingDetail.room_id == room_id)):
        raise BusinessError("Phòng đã gắn với booking, không xóa được",
                            code="ROOM_IN_USE")
    db.delete(room)
    db.commit()
    return ok({"message": "Đã xóa"})
