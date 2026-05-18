from typing import Annotated, override

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response
from jose import JWTError
from passlib import exc
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.auth.jwt_utils import create_jwt, verify_jwt
from app.backends.base import AuthBackend
from app.models import User

ph = PasswordHasher()


class JWTBackend(AuthBackend):
    @override
    @staticmethod
    def registered(db: Session, user: User, response: Response):
        jwt_token = create_jwt(user.id, user.username)
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            samesite="strict",
            max_age=60 * 60 * 24,
        )
        return {"message": "success"}

    @override
    @staticmethod
    def authenticate_request(db: Session, jwt: str):
        try:
            user_id = verify_jwt(jwt).get("id")
            user = db.get(User, user_id)
            if not user:
                raise NoResultFound
            return user
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        except NoResultFound:
            raise HTTPException(status_code=401, detail="User not found")

    @override
    @staticmethod
    def logout(response: Response, request: Request, db: Session, user: User):
        return {"message": "no logout available"}

    def __repr__(self):
        return "JWTBackend()"
