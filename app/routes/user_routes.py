from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from redis import Redis
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.auth import get_current_user
from app.auth.jwt_utils import refresh_hash
from app.auth.utils import get_auth_backend
from app.backends.jwt_backend import JWTBackend
from app.core.database import get_db
from app.core.redis import get_redis
from app.models import RefreshToken, User, UserSession
from app.schemas import SessionOutput, UserOut, UserUpdate
import logging

router = APIRouter()

db_dep = Annotated[Session, Depends(get_db)]
logger = logging.getLogger(__name__)


@router.get("/me")
def get_me(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/update-me")
def update_user(
    user_info: UserUpdate,
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
):
    try:
        user_data = user_info.model_dump(exclude_unset=True)
        if not user_data:
            return {"updated_id": user.id}
        stmt = update(User).where(User.id == user.id).values(user_data)
        db.execute(stmt)
        db.commit()
        logger.info("User %s updated fields: %s", user.id, sorted(user_data))
        return {"updated_id": user.id}
    except IntegrityError:
        db.rollback()
        logger.warning("Update conflict for user %s on fields: %s", user.id, sorted(user_data))
        raise HTTPException(status_code=400, detail="Username or email already taken")


@router.delete("/me/delete")
def delete_user(
    response: Response,
    request: Request,
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    try:
        result = get_auth_backend().delete_user(response, request, db, user, redis)
        logger.info("User %s deleted their account", user.id)
        return result
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Failed to delete user %s", user.id)
        raise e


@router.get("/me/sessions", response_model=list[SessionOutput])
def get_sessions(
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
):
    backend = get_auth_backend()
    if isinstance(backend, JWTBackend):
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.valid,
            RefreshToken.expires_at > func.now(),
        )
        resp = db.execute(stmt).scalars().all()

    else:
        stmt = select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.valid,
            UserSession.expires_at > func.now(),
        )
        resp = db.execute(stmt).scalars().all()
    logger.debug("Listed %d active session(s) for user %s", len(resp), user.id)
    return resp


@router.delete("/me/sessions/{id}")
def delete_session(
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    id: str,
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
        result = db.execute(stmt)

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
        result = db.execute(stmt)
        # Invalidate the Redis cache so authenticate_request stops honouring it.
        redis.delete(f"session:{id}")
    db.commit()
    logger.info("User %s revoked session %s (%d row(s))", user.id, id, result.rowcount)
    return {"message": "succesful"}


@router.delete("/me/sessions")
def delete_all_sessions(
    db: db_dep,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    backend = get_auth_backend()
    if isinstance(backend, JWTBackend):
        refresh_token = request.cookies.get("refresh_token")
        hashed_token = refresh_hash(refresh_token)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.valid,
                RefreshToken.hashed_token != hashed_token,
            )
            .values(valid=False)
        )
        result = db.execute(stmt)

    else:
        session_id = request.cookies.get("session_id")
        other_sessions = (
            db.execute(
                select(UserSession).where(
                    UserSession.user_id == user.id,
                    UserSession.valid,
                    UserSession.session_id != session_id,
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
                UserSession.session_id != session_id,
            )
            .values(valid=False)
        )
        result = db.execute(stmt)
    db.commit()
    logger.info(
        "User %s revoked all other sessions (%d row(s))", user.id, result.rowcount
    )
    return {"message": "succesful"}
