from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_jwt, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas import PasswordUpdate, UserCreate

router = APIRouter(prefix="/auth", tags=["Auth"])

db_dep = Annotated[Session, Depends(get_db)]


@router.post("/register")
def register(db: db_dep, new_user: UserCreate):
    user_data = new_user.model_dump()
    user_data["password"] = hash_password(user_data["password"])
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
    stmt = select(User).where(User.username == form.username)
    db_user = db.execute(stmt).scalar_one_or_none()
    if not db_user or not verify_password(form.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_jwt(db_user.id, db_user.username)
    return {"access_token": token, "token_type": "bearer"}


@router.patch("/password")
def update_password(
    db: db_dep,
    passwords: PasswordUpdate,
    user: Annotated[User, Depends(get_current_user)],
):
    if not verify_password(passwords.old_password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    user.password = hash_password(passwords.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
