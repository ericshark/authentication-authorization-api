import logging

from fastapi import HTTPException
import redis
from redis import Redis
from app.core.config import settings

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900
logger = logging.getLogger(__name__)


def increment_failed_attempts(username: str, r: Redis) -> None:
    pipe = r.pipeline()
    pipe.incr(f"failed:{username}")
    pipe.expire(f"failed:{username}", LOCKOUT_DURATION)
    pipe.execute()


def reset_failed_attempts(username, r: Redis):
    r.delete(f"failed:{username}")


def is_account_locked(username, r: Redis):
    count = r.get(f"failed:{username}")
    if count and int(count) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts try again later")


def get_redis():
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        decode_responses=True,
    )
