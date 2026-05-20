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
    def registered(db: Session, user: User, response: Response, r: Redis):

        set_jwt_cookie(response, user)
        if settings.REFRESH_TOKENS_ENABLED:
            set_refresh_cookie(response, db, user)
        return {"message": "success"}

    @override
    @staticmethod
    def authenticate_request(db: Session, jwt: str, r: Redis):
        user_id = verify_jwt(jwt).get("id")
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    @override
    @staticmethod
    def logout(response: Response, request: Request, db: Session, user: User, r: Redis):
        if not settings.REFRESH_TOKENS_ENABLED:
            return {"message": "no logout available"}
        raw_token = request.cookies.get("refresh_token")
        if not raw_token:
            raise HTTPException(status_code=400, detail="No refresh token in cookie")
        hashed_token = refresh_hash(raw_token)
        response.delete_cookie("access_token")
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

    def __repr__(self):
        return "JWTBackend()"
