import logging
import secrets
from datetime import datetime, timezone
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from redis import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from app.auth.auth import get_current_user
from app.auth.jwt_utils import refresh_hash, set_jwt_cookie
from app.auth.utils import get_auth_backend
from app.backends.jwt_backend import JWTBackend
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import (
    check_rate_limit,
    get_redis,
    increment_failed_attempts,
    is_account_locked,
    reset_failed_attempts,
)
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
ph = PasswordHasher()

db_dep = Annotated[Session, Depends(get_db)]


@router.post("/register")
def register(
    db: db_dep,
    new_user: UserCreate,
    response: Response,
    redis: Annotated[Redis, Depends(get_redis)],
):
    try:
        user_data = new_user.model_dump()
        user_data["password"] = ph.hash(user_data["password"])
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return get_auth_backend().registered(db, user, response, redis)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")


@router.post("/login")
def login(
    response: Response,
    db: db_dep,
    redis: Annotated[Redis, Depends(get_redis)],
    form: OAuth2PasswordRequestForm = Depends(),
):
    try:
        is_account_locked(form.username, redis)
        stmt = select(User).where(User.username == form.username)
        user = db.execute(stmt).scalar_one()
        if not user.is_active:
            raise HTTPException(
                status_code=400, detail="Incorrect password or username"
            )
        ph.verify(user.password, form.password)
        reset_failed_attempts(form.username, redis)
        return get_auth_backend().registered(db, user, response, redis)
    except (VerifyMismatchError, NoResultFound):
        increment_failed_attempts(form.username, redis)
        raise HTTPException(status_code=400, detail="Incorrect password or username")


@router.get("/logout")
def logout(
    response: Response,
    request: Request,
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    return get_auth_backend().logout(response, request, db, user, redis)


@router.get("/logout-all")
def logout_all(
    response: Response,
    request: Request,
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
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
    hash_token = refresh_hash(raw_token)
    stmt = select(RefreshToken).where(RefreshToken.hashed_token == hash_token)
    refresh_item = db.execute(stmt).scalar_one_or_none()
    expires_at = refresh_item.expires_at if refresh_item else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if refresh_item and refresh_item.valid and expires_at > datetime.now(timezone.utc):
        user = db.get(User, refresh_item.user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Account inactive")
        set_jwt_cookie(response, user)
        return {"message": "success new jwt"}
    raise HTTPException(status_code=401, detail="Not authorized")


@router.get("/health")
def get_health():
    pass


VERIFICATION_TOKEN_TTL = 60 * 60  # 1 hour


@router.get("/verify-user")
def request_verification(
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Account already verified")
    check_rate_limit(f"rl:verify:{user.id}", VERIFICATION_TOKEN_TTL, redis)
    token = secrets.token_hex(32)
    redis.set(f"verify:{token}", str(user.id), ex=VERIFICATION_TOKEN_TTL)
    send_verification_email_task.delay(user.email, user.email, token)
    return {"message": "Verification email sent"}


@router.get("/verify-email")
def verify_email(
    token: str,
    db: db_dep,
    redis: Annotated[Redis, Depends(get_redis)],
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
    redis: Annotated[Redis, Depends(get_redis)],
):
    check_rate_limit(f"rl:magic:{payload.email}", MAGIC_LINK_TTL, redis)
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
    response: Response,
    db: db_dep,
    redis: Annotated[Redis, Depends(get_redis)],
):
    user_id = redis.get(f"magic:{token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    redis.delete(f"magic:{token}")
    return get_auth_backend().registered(db, user, response, redis)
