import secrets
from datetime import datetime, timezone
from typing import override

from fastapi import HTTPException, Request, Response
from redis import Redis
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.backends.base import AuthBackend
from app.core.config import settings
from app.models import TOKEN_EXPIRY_SECONDS, User, UserSession
from user_agents import parse


class SessionBackend(AuthBackend):
    @override
    @staticmethod
    def registered(
        db: Session, user: User, response: Response, r: Redis, request: Request
    ):
        session_id = secrets.token_hex(32)
        r.set(f"session:{session_id}", str(user.id), ex=TOKEN_EXPIRY_SECONDS)
        ua = parse(request.headers.get("User-Agent", ""))
        device_name = f"{ua.browser.family} on {ua.os.family}"
        ip_address = (
            request.headers.get("X-Forwarded-For")
            or (request.client.host if request.client else None)
            or "unknown"
        )
        session = UserSession(
            session_id=session_id,
            user_id=user.id,
            user_agent=request.headers.get("user-agent", "unknown"),
            ip_address=ip_address.split(",")[0].strip(),
            last_active=datetime.now(timezone.utc),
            device_name=device_name,
        )
        db.add(session)
        db.commit()

        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="strict",
            secure=settings.is_production,
            max_age=TOKEN_EXPIRY_SECONDS,
        )
        return {"message": "success"}

    @override
    @staticmethod
    def authenticate_request(db: Session, request: Request, r: Redis):
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = r.get(f"session:{session_id}")
        if not user_id:
            stmt = select(UserSession).where(UserSession.session_id == session_id)
            response = db.execute(stmt).scalar_one_or_none()
            if not response:
                raise HTTPException(status_code=401, detail="Session not found")
            if not response.valid:
                raise HTTPException(status_code=401, detail="Session invalidated")

            expires_at = response.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="Session expired")
            user_id = response.user_id
        user = db.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Account inactive")
        active = r.get(f"last_active:{session_id}")
        if not active:
            r.set(f"last_active:{session_id}", 1, ex=300)
            db.execute(
                update(UserSession)
                .where(UserSession.session_id == session_id)
                .values(last_active=datetime.now(timezone.utc))
            )
            db.commit()
        return user

    @override
    @staticmethod
    def logout(response: Response, request: Request, db: Session, user: User, r: Redis):
        session_id = request.cookies.get("session_id")
        stmt = (
            update(UserSession)
            .where(UserSession.session_id == session_id)
            .values(valid=False)
        )
        db.execute(stmt)
        db.commit()
        response.delete_cookie("session_id")
        r.delete(f"session:{request.cookies.get('session_id')}")
        return {"message": "logged out"}

    @override
    @staticmethod
    def logout_all(
        response: Response, request: Request, db: Session, user: User, r: Redis
    ):
        stmt = select(UserSession).where(UserSession.user_id == user.id)
        sessions = db.execute(stmt).scalars().all()
        for session in sessions:
            r.delete(f"session:{session.session_id}")
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user.id)
            .values(valid=False)
        )
        db.execute(stmt)
        db.commit()
        response.delete_cookie("session_id")
        return {"message": "logged out"}

    @override
    @staticmethod
    def delete_user(
        response: Response, request: Request, db: Session, user: User, r: Redis
    ):
        stmt = select(UserSession).where(UserSession.user_id == user.id)
        sessions = db.execute(stmt).scalars().all()
        for session in sessions:
            r.delete(f"session:{session.session_id}")
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user.id)
            .values(valid=False)
        )
        db.execute(stmt)
        user.is_active = False
        db.commit()
        response.delete_cookie("session_id")
        return {"message": "deleted account"}

    def __repr__(self):
        return "SESSIONBackend()"
