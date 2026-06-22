import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from redis import Redis
from sqlalchemy.orm import Session

from app.auth.totp import check_enabled_2fa
from app.backends.jwt_backend import JWTBackend
from app.backends.session_backend import SessionBackend
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.models import RoleEnum, User

logger = logging.getLogger(__name__)

db_dep = Annotated[Session, Depends(get_db)]
redis_dep = Annotated[Redis, Depends(get_redis)]
check_2fa_dep = Annotated[None, Depends(check_enabled_2fa)]


@lru_cache(maxsize=1)
def get_auth_backend():
    logger.debug("Auth strategy: %s", settings.AUTH_STRATEGY)
    if settings.AUTH_STRATEGY == "JWT":
        return JWTBackend()
    if settings.AUTH_STRATEGY == "SESSION":
        return SessionBackend()
    raise ValueError(
        f"AUTH_STRATEGY must be 'JWT' or 'SESSION', got: {settings.AUTH_STRATEGY!r}"
    )


def get_current_user(
    db: db_dep,
    request: Request,
    redis: redis_dep,
) -> User:
    return get_auth_backend().authenticate_request(db, request, redis)


get_user_dep = Annotated[User, Depends(get_current_user)]


class RoleChecker:
    def __init__(self, allowed: list[RoleEnum]):
        self.allowed = allowed

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role in self.allowed:
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
