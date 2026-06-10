from datetime import datetime, timezone
from typing import override

from argon2 import PasswordHasher
from fastapi import HTTPException, Request, Response
from redis import Redis
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.auth.jwt_utils import (
    refresh_hash,
    set_jwt_cookie,
    set_refresh_cookie,
    verify_jwt,
)
from app.backends.base import AuthBackend
from app.core.config import settings
from app.models import RefreshToken, User

ph = PasswordHasher()


class JWTBackend(AuthBackend):
    @override
    @staticmethod
    def registered(
        db: Session, user: User, response: Response, r: Redis, request: Request
    ):

        set_jwt_cookie(response, user)
        if settings.REFRESH_TOKENS_ENABLED:
            set_refresh_cookie(response, db, user, request)
        return {"message": "success"}

    @override
    @staticmethod
    def authenticate_request(db: Session, request: Request, r: Redis):
        jwt = request.cookies.get("access_token")
        if not jwt:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = verify_jwt(jwt).get("id")
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Account inactive")
        return user

    @override
    @staticmethod
    def logout(response: Response, request: Request, db: Session, user: User, r: Redis):
        response.delete_cookie("access_token")
        if not settings.REFRESH_TOKENS_ENABLED:
            return {"message": "logged out"}
        raw_token = request.cookies.get("refresh_token")
        if raw_token:
            hashed_token = refresh_hash(raw_token)
            response.delete_cookie("refresh_token")
            stmt = (
                update(RefreshToken)
                .where(RefreshToken.hashed_token == hashed_token)
                .values(valid=False)
            )
            db.execute(stmt)
            db.commit()
        return {"message": "succesful logout"}

    @override
    @staticmethod
    def logout_all(
        response: Response, request: Request, db: Session, user: User, r: Redis
    ):
        if not settings.REFRESH_TOKENS_ENABLED:
            return {"message": "no logout available"}
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id)
            .values(valid=False)
        )
        db.execute(stmt)
        db.commit()
        return {"message": "succesful logout"}

    @override
    @staticmethod
    def delete_user(
        response: Response, request: Request, db: Session, user: User, r: Redis
    ):
        if settings.REFRESH_TOKENS_ENABLED:
            response.delete_cookie("refresh_token")
            stmt = (
                update(RefreshToken)
                .where(RefreshToken.user_id == user.id)
                .values(valid=False)
            )
            db.execute(stmt)
        user.is_active = False
        response.delete_cookie("access_token")
        db.commit()
        return {"message": "deleted account"}

    def __repr__(self):
        return "JWTBackend()"
