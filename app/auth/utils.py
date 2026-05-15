from functools import lru_cache

from app.backends.jwt_backend import JWTBackend
from app.backends.session_backend import SessionBackend
from app.core.config import settings


@lru_cache(maxsize=1)
def get_auth_backend():
    print(f"this is the chosen strat {settings.AUTH_STRATEGY}")
    if settings.AUTH_STRATEGY == "JWT":
        return JWTBackend()
    if settings.AUTH_STRATEGY == "SESSION":
        return SessionBackend()
    raise ValueError(
        f"AUTH_STRATEGY must be 'JWT' or 'SESSION', got: {settings.AUTH_STRATEGY!r}"
    )
