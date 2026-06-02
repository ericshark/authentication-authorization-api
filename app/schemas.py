from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import RoleEnum


class UserBase(BaseModel):
    username: str = Field(max_length=30)
    name: str | None = None
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserOut(UserBase):
    id: int
    date_created: datetime
    is_active: bool
    role: RoleEnum
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, max_length=30)
    name: str | None = None
    email: EmailStr | None = None


class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class RoleUpdate(BaseModel):
    role: RoleEnum


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class MagicLinkRequest(BaseModel):
    email: EmailStr
