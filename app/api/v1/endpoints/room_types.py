"""=========================================================================
   FILE MẪU — đã viết đầy đủ. Các endpoint khác viết theo đúng kiểu này.

   Chú ý 4 điểm:
     1. KHÔNG có select()/query() trong file endpoint thật — ở đây CRUD
        đơn giản nên gọi thẳng db cho gọn. Nghiệp vụ phức tạp (booking,
        availability) BẮT BUỘC đi qua Service.
     2. Mọi response bọc qua ok().
     3. Mỗi endpoint khai báo quyền bằng Depends(require_*).
     4. Có summary= để Swagger đọc được.
   ========================================================================="""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_admin, require_any
from app.core.exceptions import BusinessError, NotFoundError
from app.core.response import ok
from app.db.session import get_db
from app.models import Room, RoomType
from app.schemas.room import RoomTypeIn, RoomTypeOut

router = APIRouter(prefix="/room-types", tags=["02. Loại phòng"])


@router.get("", summary="Danh sách loại phòng")
def list_room_types(db: Session = Depends(get_db), _=Depends(require_any)):
    rows = db.scalars(select(RoomType).order_by(RoomType.base_price)).all()
    return ok([RoomTypeOut.model_validate(r) for r in rows])


@router.get("/{room_type_id}", summary="Chi tiết loại phòng")
def get_room_type(room_type_id: int, db: Session = Depends(get_db),
                  _=Depends(require_any)):
    rt = db.get(RoomType, room_type_id)
    if not rt:
        raise NotFoundError("RoomType", room_type_id)
    return ok(RoomTypeOut.model_validate(rt))


@router.post("", status_code=201, summary="Tạo loại phòng")
def create_room_type(dto: RoomTypeIn, db: Session = Depends(get_db),
                     _=Depends(require_admin)):
    if db.scalar(select(RoomType.id).where(RoomType.name == dto.name)):
        raise BusinessError("Tên loại phòng đã tồn tại", code="DUPLICATE_NAME")
    rt = RoomType(**dto.model_dump())
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return ok(RoomTypeOut.model_validate(rt))


@router.put("/{room_type_id}", summary="Sửa loại phòng")
def update_room_type(room_type_id: int, dto: RoomTypeIn,
                     db: Session = Depends(get_db), _=Depends(require_admin)):
    rt = db.get(RoomType, room_type_id)
    if not rt:
        raise NotFoundError("RoomType", room_type_id)
    for k, v in dto.model_dump().items():
        setattr(rt, k, v)
    db.commit()
    db.refresh(rt)
    return ok(RoomTypeOut.model_validate(rt))


@router.delete("/{room_type_id}", summary="Xóa loại phòng")
def delete_room_type(room_type_id: int, db: Session = Depends(get_db),
                     _=Depends(require_admin)):
    rt = db.get(RoomType, room_type_id)
    if not rt:
        raise NotFoundError("RoomType", room_type_id)
    if db.scalar(select(Room.id).where(Room.room_type_id == room_type_id)):
        raise BusinessError("Còn phòng thuộc loại này, không xóa được",
                            code="ROOM_TYPE_IN_USE")
    db.delete(rt)
    db.commit()
    return ok({"message": "Đã xóa"})
