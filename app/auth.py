import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, VerifyMismatchError
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RoleEnum, User

ph = PasswordHasher()

load_dotenv()
SECRET_KEY = str(os.getenv("SECRET_KEY", "default_secret_key"))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        ph.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False
    except Argon2Error as e:
        print("Unknown Error: ", e)
        return False


def create_jwt(id: int, username: str) -> str:
    payload = {
        "id": str(id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    payload = verify_jwt(token)
    user = db.get(User, int(payload["id"]))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class RoleChecker:
    def __init__(self, allowed: list[RoleEnum]):
        self.allowed = allowed

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role in self.allowed:
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
