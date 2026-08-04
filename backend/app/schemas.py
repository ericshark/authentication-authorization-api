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
    is_verified: bool
    totp_enabled: bool
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


class SessionOutput(BaseModel):
    id: str
    user_id: int
    ip_address: str | None
    device_name: str | None
    current: bool = False
    last_active: datetime | None = None
    expires_at: datetime


class Verify2fa(BaseModel):
    temp_token: str
    code: str
    user_id: int


class SecretToken(BaseModel):
    secret_token: str


class ActivityOutput(BaseModel):
    id: str
    action: str
    detail: str
    ip_address: str | None = None
    device_name: str | None = None
    created_at: datetime


class SecurityCheck(BaseModel):
    id: str
    label: str
    complete: bool
    points: int


class AccountOverview(BaseModel):
    user: UserOut
    security_score: int
    security_checks: list[SecurityCheck]
    active_sessions: int
    connected_providers: list[str]
    auth_strategy: str
