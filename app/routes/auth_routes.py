from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.jwt_utils import create_jwt
from app.auth.auth import get_current_user

from app.core.database import get_db
from app.models import User
from app.schemas import PasswordUpdate, UserCreate
from app.auth.auth import auth_strat

router = APIRouter(prefix="/auth", tags=["Auth"])
ph = PasswordHasher()

db_dep = Annotated[Session, Depends(get_db)]


@router.post("/register")
def register(db: db_dep, new_user: UserCreate):
    user_data = new_user.model_dump()
    user_data["password"] = ph.hash(user_data["password"])
    user = User(**user_data)
    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")
    db.refresh(user)
    token = create_jwt(user.id, user_data["username"])
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login")
def login(db: db_dep, form: OAuth2PasswordRequestForm = Depends()):
    return auth_strat.login(db, form)


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
    db.commit()
    return {"message": "Password updated successfully"}
