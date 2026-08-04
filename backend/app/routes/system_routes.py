from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.dependencies import db_dep, redis_dep

router = APIRouter()


@router.get("/health/live")
def liveness():
    return {
        "status": "ok",
        "service": "auth-api",
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/health/ready")
def readiness(db: db_dep, redis: redis_dep):
    components = {"database": "ok", "redis": "ok"}
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        components["database"] = "unavailable"
    try:
        redis.ping()
    except Exception:
        components["redis"] = "unavailable"

    ready = all(value == "ok" for value in components.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "degraded",
            "components": components,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/auth/capabilities")
def capabilities():
    return {
        "auth_strategy": settings.AUTH_STRATEGY,
        "refresh_tokens": settings.REFRESH_TOKENS_ENABLED,
        "two_factor_auth": settings.TOTP,
        "oauth": {
            "google": bool(settings.GOOGLE_CLIENT_ID),
            "github": bool(settings.GITHUB_CLIENT_ID),
        },
        "features": [
            "password_login",
            "magic_links",
            "email_verification",
            "device_sessions",
            "security_activity",
            "account_export",
            "role_based_access",
        ],
    }
