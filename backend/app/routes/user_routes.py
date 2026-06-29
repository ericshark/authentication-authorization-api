import logging

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.auth.tokens import hash_token
from app.backends.jwt_backend import JWTBackend
from app.core.dependencies import (
    db_dep,
    get_auth_backend,
    get_user_dep,
    redis_dep,
)
from app.models import RefreshToken, User, UserSession
from app.schemas import SessionOutput, UserOut, UserUpdate

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/me")
def get_me(user: get_user_dep) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/update-me")
def update_user(
    user_info: UserUpdate,
    db: db_dep,
    user: get_user_dep,
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
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Failed to delete user %s", user.id)
        raise e


@router.get("/me/sessions", response_model=list[SessionOutput])
def get_sessions(
    db: db_dep,
    user: get_user_dep,
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
    user: get_user_dep,
    redis: redis_dep,
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
    user: get_user_dep,
    redis: redis_dep,
):
    backend = get_auth_backend()
    if isinstance(backend, JWTBackend):
        refresh_token = request.cookies.get("refresh_token")
        hashed_token = hash_token(refresh_token)
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
