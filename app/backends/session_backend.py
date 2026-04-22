from app.backends.base import AuthBackend
from app.core.redis import get_redis

r = get_redis()
r = get_redis()

# # store a session with 24 hour expiry
# r.set(f"session:{session_id}", str(user_id), ex=86400)

# # retrieve
# user_id = r.get(f"session:{session_id}")  # returns None if not found

# # delete on logout
# r.delete(f"session:{session_id}")

# # check if exists
# exists = r.exists(f"session:{session_id}")  # returns 1 or 0


class SessionBackend(AuthBackend):
    pass
