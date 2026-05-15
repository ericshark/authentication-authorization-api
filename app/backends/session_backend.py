from datetime import datetime, timedelta
from typing import Annotated, override

from jose import exceptions
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backends.base import AuthBackend
from app.core.database import get_db
from app.core.redis import get_redis
from app.models import User, UserSession
from fastapi import Cookie, Depends, Response
import secrets
from app.core.config import settings

r = get_redis()


# # store a session with 24 hour expiry
# r.set(f"session:{session_id}", str(user_id), ex=86400)

# # retrieve
# user_id = r.get(f"session:{session_id}")  # returns None if not found

# # delete on logout
# r.delete(f"session:{session_id}")

# # check if exists
# exists = r.exists(f"session:{session_id}")  # returns 1 or 0


class SessionBackend(AuthBackend):
    @override
    @staticmethod
    def registered(db: Session, user: User, response: Response):
        try:
            session_id = secrets.token_hex(32)
            r.set(f"session:{session_id}", str(user.id), ex=60 * 60 * 24 * 30)
            session = UserSession(
                session_id=session_id,
                user_id=user.id,
            )
            db.add(session)
            db.commit()

            response.set_cookie(
                key="session_id",
                value=session_id,
                httponly=True,
                samesite="strict",
                secure=True,
                max_age=60 * 60 * 24 * 30,
            )
        except Exception as e:
            raise e

    @override
    @staticmethod
    def authenticate_request(db: Session, session_id: str):
        try:
            user_id = r.get(f"session:{session_id}")
            if not user_id:
                stmt = select(UserSession).where(UserSession.session_id == session_id)
                response = db.execute(stmt).scalar_one()
                user_id = response.user_id
            user = db.get(User, user_id)
            return user
        except Exception as e:
            raise e

    def logout(response: Response, db: Session, user: User):
        response.delete_cookie("session_id")

    def __repr__(self):
        return "SESSIONBackend()"
