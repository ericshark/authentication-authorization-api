from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


TOKEN_EXPIRY_DAYS = 30
TOKEN_EXPIRY_SECONDS = TOKEN_EXPIRY_DAYS * 24 * 60 * 60


class RoleEnum(Enum):
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(nullable=True)
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str | None] = mapped_column(nullable=True)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[RoleEnum] = mapped_column(
        SQLAlchemyEnum(RoleEnum), default=RoleEnum.USER
    )

    def __repr__(self):
        return f"id: {self.id}, username: {self.username}"


class UserSession(Base):
    __tablename__ = "session"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))
    valid: Mapped[bool] = mapped_column(Boolean, default=True)
    user_agent: Mapped[str] = mapped_column(nullable=True)
    ip_address: Mapped[str] = mapped_column(nullable=True)
    last_active: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    device_name: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    hashed_token: Mapped[str] = mapped_column(unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))
    valid: Mapped[bool] = mapped_column(Boolean, default=True)
    family_id: Mapped[str]
    user_agent: Mapped[str]
    ip_address: Mapped[str]
    device_name: Mapped[str]
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS),
    )


class SocialAccount(Base):
    __tablename__ = "social_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str]
    provider_id: Mapped[str] = mapped_column(unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))
    user: Mapped["User"] = relationship()
