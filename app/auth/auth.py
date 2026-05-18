from typing import Annotated

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Cookie, Response, Request
from fastapi.security import OAuth2PasswordBearer


from sqlalchemy.orm import Session

from app.auth.utils import get_auth_backend
from app.core.database import get_db
from app.models import RoleEnum, User


ph = PasswordHasher()


def get_current_user(db: Annotated[Session, Depends(get_db)], request: Request) -> User:
    if "session_id" not in request.cookies and "access_token" not in request.cookies:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return get_auth_backend().authenticate_request(
        db, request.cookies.get("session_id") or request.cookies.get("access_token")
    )


class RoleChecker:
    def __init__(self, allowed: list[RoleEnum]):
        self.allowed = allowed

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role in self.allowed:
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
