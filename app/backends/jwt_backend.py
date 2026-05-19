import secrets
from typing import override

from argon2 import PasswordHasher
from fastapi import HTTPException, Request, Response
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.auth.jwt_utils import (
    create_jwt,
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
    def registered(db: Session, user: User, response: Response):
        jwt_token = create_jwt(user.id, user.username)
        set_jwt_cookie(response, jwt_token)
        if settings.REFRESH_TOKENS_ENABLED:
            refresh_token = secrets.token_hex(32)
            set_refresh_cookie(response, refresh_token)
            hash_token = refresh_hash(refresh_token)
            user_refresh = RefreshToken(user_id=user.id, hashed_token=hash_token)
            db.add(user_refresh)
            db.commit()
        return {"message": "success"}

    @override
    @staticmethod
    def authenticate_request(db: Session, jwt: str):
        user_id = verify_jwt(jwt).get("id")
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    @override
    @staticmethod
    def logout(response: Response, request: Request, db: Session, user: User):
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
    def logout_all(response: Response, request: Request, db: Session, user: User):
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
