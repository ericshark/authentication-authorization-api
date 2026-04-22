from functools import lru_cache

from app.backends.jwt_backend import JWTBackend
from app.backends.session_backend import SessionBackend
from app.core.config import settings

auth_strat = settings.AUTH_STRATEGY


@lru_cache(maxsize=1)
def get_auth_backend():
    if auth_strat == "JWT":
        backend = JWTBackend()
        return backend
    if auth_strat == "SESSION":
        backend = SessionBackend()
        return backend

    else:
        raise ValueError(
            f"AUTH_STRATEGY must be 'JWT' or 'SESSION', got: {auth_strat!r}"
        )
