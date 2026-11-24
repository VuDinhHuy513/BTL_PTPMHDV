from pydantic import BaseModel, ConfigDict

# Phân trang dùng chung cho mọi API danh sách (bookings, customers...).
# MAX chặn client xin limit=100000 làm nặng DB.
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    message: str
