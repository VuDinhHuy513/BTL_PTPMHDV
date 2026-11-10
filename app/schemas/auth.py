from pydantic import BaseModel, Field

from app.models.enums import Role
from app.schemas.common import ORMBase


class LoginIn(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int          # số giây access_token còn sống


class UserOut(ORMBase):
    id: int
    username: str
    full_name: str
    role: Role
    is_active: bool
    # KHÔNG có password_hash — tuyệt đối không trả mật khẩu (dù đã hash) ra API


class UserCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6)
    role: Role = Role.RECEPTIONIST


class UserUpdateIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    role: Role
