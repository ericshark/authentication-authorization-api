import json
import logging
from datetime import datetime, timezone

from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

ACTIVITY_LIMIT = 50


def record_activity(
    redis: Redis,
    user_id: int,
    action: str,
    *,
    detail: str,
    ip_address: str | None = None,
    device_name: str | None = None,
) -> None:
    event = {
        "id": f"{datetime.now(timezone.utc).timestamp():.6f}",
        "action": action,
        "detail": detail,
        "ip_address": ip_address,
        "device_name": device_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    key = f"activity:{user_id}"
    try:
        redis.lpush(key, json.dumps(event))
        redis.ltrim(key, 0, ACTIVITY_LIMIT - 1)
    except RedisError:
        logger.warning("Could not record activity for user %s", user_id, exc_info=True)


def list_activity(redis: Redis, user_id: int, limit: int) -> list[dict]:
    try:
        items = redis.lrange(f"activity:{user_id}", 0, limit - 1)
        return [json.loads(item) for item in items]
    except (RedisError, json.JSONDecodeError):
        logger.warning("Could not load activity for user %s", user_id, exc_info=True)
        return []
