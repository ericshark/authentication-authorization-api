from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.security import OAuth2PasswordRequestForm


from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session


from app.auth.auth import get_current_user

from app.core.database import get_db
from app.models import User
from app.schemas import PasswordUpdate, UserCreate
from app.auth.utils import get_auth_backend

router = APIRouter(prefix="/auth", tags=["Auth"])
ph = PasswordHasher()

db_dep = Annotated[Session, Depends(get_db)]


@router.post("/register")
def register(db: db_dep, new_user: UserCreate, response: Response):
    try:
        user_data = new_user.model_dump()
        user_data["password"] = ph.hash(user_data["password"])
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return get_auth_backend().registered(db, user, response)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")


@router.post("/login")
def login(response: Response, db: db_dep, form: OAuth2PasswordRequestForm = Depends()):
    try:
        stmt = select(User).where(User.username == form.username)
        user = db.execute(stmt).scalar_one()
        ph.verify(user.password, form.password)
        return get_auth_backend().registered(db, user, response)
    except (VerifyMismatchError, NoResultFound):
        raise HTTPException(status_code=400, detail="Incorrect password or username")


@router.get("/logout")
def logout(
    response: Response,
    request: Request,
    db: db_dep,
    user: Annotated[User, Depends(get_current_user)],
):
    return get_auth_backend().logout(response, request, db, user)


@router.patch("/password")
def update_password(
    db: db_dep,
    passwords: PasswordUpdate,
    user: Annotated[User, Depends(get_current_user)],
):
    try:
        ph.verify(user.password, passwords.old_password)
    except VerifyMismatchError:
        raise HTTPException(status_code=400, detail="Incorrect password")
    user.password = ph.hash(passwords.new_password)
    db.add(user)
    db.commit()
    return {"message": "Password updated successfully"}
