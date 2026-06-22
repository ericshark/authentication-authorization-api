import logging
import secrets
from datetime import datetime, timezone
from typing import Annotated

from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, NoResultFound

from app.auth.cookies import set_jwt_cookie, set_refresh
from app.auth.lockout import (
    increment_limit,
    is_limit_reached,
)
from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import hash_token
from app.backends.jwt_backend import JWTBackend
from app.core.config import settings
from app.core.dependencies import db_dep, get_auth_backend, get_current_user, redis_dep
from app.models import RefreshToken, User
from app.schemas import (
    MagicLinkRequest,
    UserCreate,
)
from app.tasks.email_tasks import (
    send_magic_link_task,
    send_verification_email_task,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register")
def register(
    db: db_dep,
    new_user: UserCreate,
    request: Request,
    response: Response,
    redis: redis_dep,
):
    try:
        user_data = new_user.model_dump()
        user_data["password"] = hash_password(user_data["password"])
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return get_auth_backend().registered(db, user, response, redis, request)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")


@router.post("/login")
def login(
    request: Request,
    response: Response,
    db: db_dep,
    redis: redis_dep,
    form: OAuth2PasswordRequestForm = Depends(),
):
    key = f"failed:{form.username}"
    try:
        is_limit_reached(key, redis)
        stmt = select(User).where(User.username == form.username)
        user = db.execute(stmt).scalar_one()
        if not user.is_active:
            raise HTTPException(
                status_code=400, detail="Incorrect password or username"
            )
        verify_password(user.password, form.password)
        redis.delete(key)
        if settings.TOTP and user.totp_enabled:
            temp_token = secrets.token_hex(32)
            redis.set(f"2faTempToken:{user.id}", temp_token, ex=60 * 5)
            return {"requires_2fa": True, "temp_token": temp_token, "user_id": user.id}

        return get_auth_backend().registered(db, user, response, redis, request)
    except (VerifyMismatchError, NoResultFound):
        increment_limit(key, redis)
        raise HTTPException(status_code=400, detail="Incorrect password or username")


@router.get("/logout")
def logout(
    response: Response,
    request: Request,
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
    redis: redis_dep,
):
    return get_auth_backend().logout(response, request, db, user, redis)


@router.get("/logout-all")
def logout_all(
    response: Response,
    request: Request,
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
    redis: redis_dep,
):
    return get_auth_backend().logout_all(response, request, db, user, redis)


@router.get("/refresh")
def refresh_token(
    response: Response,
    request: Request,
    db: db_dep,
):
    if not settings.REFRESH_TOKENS_ENABLED or not isinstance(
        get_auth_backend(), JWTBackend
    ):
        raise HTTPException(status_code=404, detail="Not found")
    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    hashed_token = hash_token(raw_token)
    stmt = select(RefreshToken).where(RefreshToken.hashed_token == hashed_token)
    refresh_item = db.execute(stmt).scalar_one_or_none()
    if not refresh_item:
        raise HTTPException(status_code=401, detail="Not authorized")
    expires_at = refresh_item.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Not authorized")
    if not refresh_item.valid:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == refresh_item.family_id)
            .values(valid=False)
        )
        db.execute(stmt)
        db.commit()
        raise HTTPException(status_code=401, detail="Not authorized")
    user = db.get(User, refresh_item.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    refresh_item.valid = False
    set_refresh(response, db, user, request, refresh_item.family_id)
    set_jwt_cookie(response, user)
    db.commit()
    return {"message": "success new jwt"}


@router.get("/health")
def get_health():
    pass


VERIFICATION_TOKEN_TTL = 60 * 60  # 1 hour


@router.get("/verify-user")
def request_verification(
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
    redis: redis_dep,
):
    key = f"rl:verify:{user.id}"
    is_limit_reached(key, redis)
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Account already verified")
    increment_limit(key, redis, window=VERIFICATION_TOKEN_TTL)
    token = secrets.token_hex(32)
    redis.set(f"verify:{token}", str(user.id), ex=VERIFICATION_TOKEN_TTL)
    send_verification_email_task.delay(user.email, user.email, token)
    return {"message": "Verification email sent"}


@router.get("/verify-email")
def verify_email(
    token: str,
    db: db_dep,
    redis: redis_dep,
):
    user_id = redis.get(f"verify:{token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    redis.delete(f"verify:{token}")
    db.commit()
    return {"message": "Email verified successfully"}


MAGIC_LINK_TTL = 60 * 15  # 15 minutes


@router.post("/magic-link")
def request_magic_link(
    payload: MagicLinkRequest,
    db: db_dep,
    redis: redis_dep,
):
    key = f"rl:magic:{payload.email}"
    is_limit_reached(key, redis)
    increment_limit(key, redis, window=VERIFICATION_TOKEN_TTL)
    stmt = select(User).where(User.email == payload.email)
    user = db.execute(stmt).scalar_one_or_none()
    if user and user.is_active:
        token = secrets.token_hex(32)
        redis.set(f"magic:{token}", str(user.id), ex=MAGIC_LINK_TTL)
        send_magic_link_task.delay(user.email, user.email, token)
    return {"message": "If that email is registered, a magic link has been sent"}


@router.get("/magic-link/verify")
def verify_magic_link(
    token: str,
    request: Request,
    response: Response,
    db: db_dep,
    redis: redis_dep,
):
    user_id = redis.get(f"magic:{token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    redis.delete(f"magic:{token}")
    return get_auth_backend().registered(db, user, response, redis, request)
