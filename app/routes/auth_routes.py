import logging
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
from app.models import RefreshToken, User
from app.schemas import PasswordUpdate, UserCreate
from app.core.redis import get_redis
from app.core.redis import (
    increment_failed_attempts,
    is_account_locked,
    reset_failed_attempts,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])
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


@router.patch("/password")
def update_password(
    response: Response,
    request: Request,
    db: db_dep,
    passwords: PasswordUpdate,
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    try:
        ph.verify(user.password, passwords.old_password)
    except VerifyMismatchError:
        raise HTTPException(status_code=400, detail="Incorrect password")
    user.password = ph.hash(passwords.new_password)
    db.commit()
    get_auth_backend().logout_all(response, request, db, user, redis)
    return {"message": "Password updated successfully"}


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
        set_jwt_cookie(response, user)
        return {"message": "success new jwt"}
    raise HTTPException(status_code=401, detail="Not authorized")


@router.get("/health")
def get_health():
    pass
