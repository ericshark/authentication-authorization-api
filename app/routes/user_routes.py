from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from redis import Redis
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.auth import get_current_user
from app.auth.utils import get_auth_backend
from app.core.database import get_db
from app.core.redis import get_redis
from app.models import User
from app.schemas import UserOut, UserUpdate

router = APIRouter()

db_dep = Annotated[Session, Depends(get_db)]


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
        return {"updated_id": user.id}
    except IntegrityError:
        db.rollback()
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
        return get_auth_backend().delete_user(response, request, db, user, redis)
    except SQLAlchemyError as e:
        db.rollback()
        raise e


@router.get("/me/sessions")
def get_sessions(
    response: Response,
    request: Request,
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    pass


@router.delete("/me/sessions/{id}")
def delete_session(user_id: str):
    pass


@router.delete("/me/sessions")
def delete_all_sessions():
    pass
