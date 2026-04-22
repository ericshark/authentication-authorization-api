from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, String, func
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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


class Session(Base):
    pass
