from typing import Annotated

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request
from redis import Redis
from sqlalchemy.orm import Session

from app.auth.utils import get_auth_backend
from app.backends.session_backend import SessionBackend
from app.core.database import get_db
from app.core.redis import get_redis
from app.models import RoleEnum, User

ph = PasswordHasher()


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
) -> User:
    backend = get_auth_backend()

    if isinstance(backend, SessionBackend):
        token = request.cookies.get("session_id")
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return backend.authenticate_request(db, token, redis)


class RoleChecker:
    def __init__(self, allowed: list[RoleEnum]):
        self.allowed = allowed

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role in self.allowed:
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
