import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, override

from fastapi import Cookie, Depends, HTTPException, Response, Request
from jose import exceptions
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.backends.base import AuthBackend
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.models import User, UserSession

logger = logging.getLogger(__name__)

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
            return {"message": "success"}
        except Exception as e:
            logger.exception("Session registration failed")
            raise e

    @override
    @staticmethod
    def authenticate_request(db: Session, session_id: str):
        user_id = r.get(f"session:{session_id}")
        if not user_id:
            stmt = select(UserSession).where(UserSession.session_id == session_id)
            response = db.execute(stmt).scalar_one_or_none()
            if not response:
                raise HTTPException(status_code=401, detail="Session not found")
            if not response.valid:
                raise HTTPException(status_code=401, detail="Session invalidated")

            if response.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="Session expired")
            user_id = response.user_id
        user = db.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    @override
    @staticmethod
    def logout(response: Response, request: Request, db: Session, user: User):
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user.id)
            .values(valid=False)
        )
        db.execute(stmt)
        db.commit()
        response.delete_cookie("session_id")
        r.delete(f"session:{request.cookies.get('session_id')}")
        return {"message": "logged out"}

    def __repr__(self):
        return "SESSIONBackend()"
