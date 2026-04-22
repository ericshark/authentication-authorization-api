from typing import Annotated, override

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from passlib import exc
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from argon2.exceptions import VerifyMismatchError

from app.backends.base import AuthBackend
from app.core.database import get_db
from app.models import User
from app.auth.jwt_utils import create_jwt, verify_jwt

db_dep = Annotated[Session, Depends(get_db)]
ph = PasswordHasher()


class JWTBackend(AuthBackend):
    @override
    @staticmethod
    def login(self, db: Session, form: OAuth2PasswordRequestForm):
        try:
            stmt = select(User).where(User.username == form.username)
            user = db.execute(stmt).scalar_one()
            ph.verify(user.password, form.password)
            token = create_jwt(user.id, user.username)
            return {"access_token": token, "token_type": "bearer"}
        except VerifyMismatchError:
            raise HTTPException(status_code=400, detail="Incorrect password")

    @override
    @staticmethod
    def authenticate_request(db: Session, jwt: OAuth2PasswordBearer):
        try:
            user_id = verify_jwt(jwt).get("id")
            user = db.get(User, user_id)
            return user
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        except NoResultFound:
            raise HTTPException(status_code=401, detail="User not found")

    def __repr__(self):
        return "JWTBackend()"
