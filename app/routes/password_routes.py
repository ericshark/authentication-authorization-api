import logging
import secrets

from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select

from app.auth.lockout import increment_limit, is_limit_reached
from app.auth.passwords import hash_password, verify_password
from app.core.dependencies import db_dep, get_auth_backend, get_user_dep, redis_dep
from app.models import User
from app.schemas import (
    ForgotPasswordRequest,
    PasswordUpdate,
    ResetPasswordRequest,
)
from app.tasks.email_tasks import (
    send_password_reset_task,
)

logger = logging.getLogger(__name__)

router = APIRouter()


PASSWORD_RESET_TTL = 60 * 15  # 15 minutes


@router.patch("/password")
def update_password(
    response: Response,
    request: Request,
    db: db_dep,
    passwords: PasswordUpdate,
    user: get_user_dep,
    redis: redis_dep,
):
    try:
        verify_password(user.password, passwords.old_password)
    except VerifyMismatchError:
        raise HTTPException(status_code=400, detail="Incorrect password")
    user.password = hash_password(passwords.new_password)
    db.commit()
    get_auth_backend().logout_all(response, request, db, user, redis)
    return {"message": "Password updated successfully"}


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    db: db_dep,
    redis: redis_dep,
):
    stmt = select(User).where(User.email == payload.email)
    user = db.execute(stmt).scalar_one_or_none()
    if user and user.is_active:
        key = f"rl:reset:{payload.email}"
        is_limit_reached(key, redis)
        increment_limit(key, redis)
        token = secrets.token_hex(32)
        redis.set(f"reset:{token}", str(user.id), ex=PASSWORD_RESET_TTL)
        send_password_reset_task.delay(user.email, user.email, token)
    return {"message": "If that email is registered, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    db: db_dep,
    redis: redis_dep,
):
    user_id = redis.get(f"reset:{payload.token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = hash_password(payload.new_password)
    redis.delete(f"reset:{payload.token}")
    db.commit()
    return {"message": "Password reset successfully"}
