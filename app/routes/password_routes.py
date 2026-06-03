import logging
import secrets
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.auth import get_current_user
from app.auth.utils import get_auth_backend
from app.core.database import get_db
from app.core.redis import (
    check_rate_limit,
    get_redis,
)
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
ph = PasswordHasher()

db_dep = Annotated[Session, Depends(get_db)]

PASSWORD_RESET_TTL = 60 * 15  # 15 minutes


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


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    db: db_dep,
    redis: Annotated[Redis, Depends(get_redis)],
):
    check_rate_limit(f"rl:reset:{payload.email}", PASSWORD_RESET_TTL, redis)
    stmt = select(User).where(User.email == payload.email)
    user = db.execute(stmt).scalar_one_or_none()
    if user and user.is_active:
        token = secrets.token_hex(32)
        redis.set(f"reset:{token}", str(user.id), ex=PASSWORD_RESET_TTL)
        send_password_reset_task.delay(user.email, user.email, token)
    return {"message": "If that email is registered, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    db: db_dep,
    redis: Annotated[Redis, Depends(get_redis)],
):
    user_id = redis.get(f"reset:{payload.token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = ph.hash(payload.new_password)
    redis.delete(f"reset:{payload.token}")
    db.commit()
    return {"message": "Password reset successfully"}
