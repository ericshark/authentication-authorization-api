import logging

from fastapi import HTTPException
from redis import Redis

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 60 * 5
RATE_LIMIT_MAX_REQUESTS = 3
logger = logging.getLogger(__name__)


def is_limit_reached(
    key: str,
    r: Redis,
    max_requests: int = RATE_LIMIT_MAX_REQUESTS,
):
    count = r.get(key)
    if count and int(count) >= max_requests:
        raise HTTPException(status_code=429, detail="Too many attempts try again later")


def reset_failed_attempts(username: str, r: Redis) -> None:
    r.delete(f"failed:{username}")


def increment_limit(
    key: str,
    r: Redis,
    max_requests: int = RATE_LIMIT_MAX_REQUESTS,
    window: int = LOCKOUT_DURATION,
) -> None:
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window, nx=True)
    results = pipe.execute()
    count = results[0]
    if count > max_requests:
        raise HTTPException(
            status_code=429, detail="Too many requests, try again later"
        )
