from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import RoleEnum


class UserBase(BaseModel):
    username: str
    name: str | None = None
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    date_created: datetime
    is_active: bool
    role: RoleEnum
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    username: str | None = None
    name: str | None = None
    email: EmailStr | None = None


class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str


class RoleUpdate(BaseModel):
    role: RoleEnum
