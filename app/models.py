import datetime

from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, String, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user_account"

    id : Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True,nullable=False)
    name: Mapped[str | None] = mapped_column(nullable=True)
    email : Mapped[str] = mapped_column(unique=True)
    password : Mapped[str]
    date_created : Mapped[datetime] = mapped_column(default=func.now())
    is_active : Mapped[bool] = mapped_column(Boolean, default = True)


    def __repr__(self):
        return f"id: {self.id}, username: {self.username}"




# class Addresss(Base):
#     __tablename__ = "addresss"

#     id : Mapped[int] = mapped_column(primary_key=True)
#     address: Mapped[str] = mapped_column(String(255))
#     user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))

#     user: Mapped[User] = relationship(back_populates="addresses")


