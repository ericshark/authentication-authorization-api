from typing import Annotated

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request
from redis import Redis
from sqlalchemy.orm import Session

from app.auth.utils import get_auth_backend
from app.core.database import get_db
from app.core.redis import get_redis
from app.models import RoleEnum, User

ph = PasswordHasher()


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
) -> User:
    return get_auth_backend().authenticate_request(db, request, redis)


class RoleChecker:
    def __init__(self, allowed: list[RoleEnum]):
        self.allowed = allowed

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role in self.allowed:
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
