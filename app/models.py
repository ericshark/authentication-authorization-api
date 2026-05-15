from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
    password: Mapped[str]
    date_created: Mapped[datetime] = mapped_column(default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
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
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc) + timedelta(days=18)
    )
