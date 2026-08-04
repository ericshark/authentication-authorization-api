import logging
import secrets
from datetime import datetime, timezone

import pyotp
from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.auth.request_info import get_device_name, get_ip_address
from app.auth.tokens import hash_token
from app.auth.totp import decrypt_secret
from app.backends.jwt_backend import JWTBackend
from app.core.config import settings
from app.core.dependencies import (
    check_2fa_dep,
    db_dep,
    get_auth_backend,
    get_user_dep,
    redis_dep,
)
from app.models import RefreshToken, SocialAccount, User, UserSession
from app.schemas import (
    AccountOverview,
    ActivityOutput,
    SecretToken,
    SessionOutput,
    UserOut,
    UserUpdate,
)
from app.services.activity_service import list_activity, record_activity

router = APIRouter()
logger = logging.getLogger(__name__)


def _active_session_rows(db, user: User):
    backend = get_auth_backend()
    model = RefreshToken if isinstance(backend, JWTBackend) else UserSession
    return (
        db.execute(
            select(model).where(
                model.user_id == user.id,
                model.valid,
                model.expires_at > func.now(),
            )
        )
        .scalars()
        .all()
    )


def _security_checks(user: User, session_count: int, providers: list[str]):
    return [
        {
            "id": "email",
            "label": "Email verified",
            "complete": user.is_verified,
            "points": 25,
        },
        {
            "id": "two_factor",
            "label": "Two-factor authentication",
            "complete": user.totp_enabled,
            "points": 35,
        },
        {
            "id": "password",
            "label": "Password sign-in available",
            "complete": bool(user.password),
            "points": 20,
        },
        {
            "id": "sessions",
            "label": "Three or fewer active sessions",
            "complete": session_count <= 3,
            "points": 10,
        },
        {
            "id": "recovery",
            "label": "Recovery provider connected",
            "complete": bool(providers),
            "points": 10,
        },
    ]


@router.get("/me")
def get_me(user: get_user_dep) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/me/overview", response_model=AccountOverview)
def get_overview(db: db_dep, user: get_user_dep):
    sessions = _active_session_rows(db, user)
    providers = list(
        db.execute(
            select(SocialAccount.provider).where(SocialAccount.user_id == user.id)
        ).scalars()
    )
    checks = _security_checks(user, len(sessions), providers)
    return {
        "user": UserOut.model_validate(user),
        "security_score": sum(item["points"] for item in checks if item["complete"]),
        "security_checks": checks,
        "active_sessions": len(sessions),
        "connected_providers": providers,
        "auth_strategy": settings.AUTH_STRATEGY,
    }


@router.get("/me/activity", response_model=list[ActivityOutput])
def get_activity(
    user: get_user_dep,
    redis: redis_dep,
    limit: int = Query(default=20, ge=1, le=50),
):
    return list_activity(redis, user.id, limit)


@router.get("/me/export")
def export_account(db: db_dep, user: get_user_dep):
    sessions = _active_session_rows(db, user)
    providers = list(
        db.execute(
            select(SocialAccount.provider).where(SocialAccount.user_id == user.id)
        ).scalars()
    )
    return {
        "generated_at": datetime.now(timezone.utc),
        "profile": UserOut.model_validate(user),
        "security": {
            "two_factor_enabled": user.totp_enabled,
            "active_sessions": len(sessions),
            "connected_providers": providers,
        },
    }


@router.patch("/update-me")
def update_user(
    user_info: UserUpdate,
    request: Request,
    db: db_dep,
    user: get_user_dep,
    redis: redis_dep,
):
    user_data = user_info.model_dump(exclude_unset=True)
    try:
        if not user_data:
            return {"updated_id": user.id}
        db.execute(update(User).where(User.id == user.id).values(user_data))
        db.commit()
        record_activity(
            redis,
            user.id,
            "profile.updated",
            detail=f"Updated {', '.join(sorted(user_data))}",
            ip_address=get_ip_address(request),
            device_name=get_device_name(request),
        )
        logger.info("User %s updated fields: %s", user.id, sorted(user_data))
        return {"updated_id": user.id}
    except IntegrityError:
        db.rollback()
        logger.warning(
            "Update conflict for user %s on fields: %s", user.id, sorted(user_data)
        )
        raise HTTPException(status_code=400, detail="Username or email already taken")


@router.delete("/me/delete")
def delete_user(
    response: Response,
    request: Request,
    db: db_dep,
    user: get_user_dep,
    redis: redis_dep,
):
    try:
        result = get_auth_backend().delete_user(response, request, db, user, redis)
        logger.info("User %s deleted their account", user.id)
        return result
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to delete user %s", user.id)
        raise exc


@router.get("/me/sessions", response_model=list[SessionOutput])
def get_sessions(request: Request, db: db_dep, user: get_user_dep):
    backend = get_auth_backend()
    sessions = _active_session_rows(db, user)
    if isinstance(backend, JWTBackend):
        raw_token = request.cookies.get("refresh_token")
        current_id = hash_token(raw_token) if raw_token else None
        response = [
            {
                "id": session.hashed_token,
                "user_id": session.user_id,
                "ip_address": session.ip_address,
                "device_name": session.device_name,
                "current": session.hashed_token == current_id,
                "last_active": None,
                "expires_at": session.expires_at,
            }
            for session in sessions
        ]
    else:
        current_id = request.cookies.get("session_id")
        response = [
            {
                "id": session.session_id,
                "user_id": session.user_id,
                "ip_address": session.ip_address,
                "device_name": session.device_name,
                "current": session.session_id == current_id,
                "last_active": session.last_active,
                "expires_at": session.expires_at,
            }
            for session in sessions
        ]
    logger.debug("Listed %d active session(s) for user %s", len(response), user.id)
    return response


@router.delete("/me/sessions/{id}")
def delete_session(
    id: str,
    request: Request,
    db: db_dep,
    user: get_user_dep,
    redis: redis_dep,
):
    backend = get_auth_backend()
    if isinstance(backend, JWTBackend):
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.valid,
                RefreshToken.hashed_token == id,
            )
            .values(valid=False)
        )
    else:
        stmt = (
            update(UserSession)
            .where(
                UserSession.user_id == user.id,
                UserSession.valid,
                UserSession.session_id == id,
            )
            .values(valid=False)
        )
        redis.delete(f"session:{id}")
    result = db.execute(stmt)
    db.commit()
    if result.rowcount:
        record_activity(
            redis,
            user.id,
            "session.revoked",
            detail="Revoked a device session",
            ip_address=get_ip_address(request),
            device_name=get_device_name(request),
        )
    logger.info("User %s revoked session %s (%d row(s))", user.id, id, result.rowcount)
    return {"message": "Session revoked", "revoked": bool(result.rowcount)}


@router.delete("/me/sessions")
def delete_all_sessions(
    db: db_dep,
    request: Request,
    user: get_user_dep,
    redis: redis_dep,
):
    backend = get_auth_backend()
    if isinstance(backend, JWTBackend):
        refresh_token = request.cookies.get("refresh_token")
        current_id = hash_token(refresh_token) if refresh_token else ""
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.valid,
                RefreshToken.hashed_token != current_id,
            )
            .values(valid=False)
        )
    else:
        current_id = request.cookies.get("session_id")
        other_sessions = (
            db.execute(
                select(UserSession).where(
                    UserSession.user_id == user.id,
                    UserSession.valid,
                    UserSession.session_id != current_id,
                )
            )
            .scalars()
            .all()
        )
        for session in other_sessions:
            redis.delete(f"session:{session.session_id}")
        stmt = (
            update(UserSession)
            .where(
                UserSession.user_id == user.id,
                UserSession.valid,
                UserSession.session_id != current_id,
            )
            .values(valid=False)
        )
    result = db.execute(stmt)
    db.commit()
    record_activity(
        redis,
        user.id,
        "sessions.revoked",
        detail=f"Revoked {result.rowcount} other session(s)",
        ip_address=get_ip_address(request),
        device_name=get_device_name(request),
    )
    return {"message": "Other sessions revoked", "revoked": result.rowcount}


@router.post("/me/backup-codes/regenerate")
def regenerate_backup_codes(
    payload: SecretToken,
    db: db_dep,
    user: get_user_dep,
    redis: redis_dep,
    _: check_2fa_dep,
):
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    secret = decrypt_secret(user.totp_secret)
    if not pyotp.TOTP(secret).verify(payload.secret_token, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid code")
    backup_codes = [f"{secrets.token_hex(4)}-{secrets.token_hex(4)}" for _ in range(10)]
    user.backup_codes = [hash_token(code) for code in backup_codes]
    db.commit()
    record_activity(
        redis,
        user.id,
        "backup_codes.regenerated",
        detail="Generated a new set of one-time recovery codes",
    )
    return {"backup_codes": backup_codes}
