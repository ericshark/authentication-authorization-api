from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Annotated
from app.database import get_db
from app.models import User
from app.schemas import UpdatePassword, UserCreate
from app.auth import hashPass, createJWT, verifyJWT, verifyPass, oauth2_scheme, get_current_user
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter(
    prefix= "/auth",
    tags = ["Auth"]
)

db_deb = Annotated[Session, Depends(get_db)]



@router.post('/createUser' )
def createUser(db: db_deb, new_user: UserCreate):
    user_data = new_user.model_dump()
    user_data["password"] = hashPass(user_data["password"])
    
    user = User(**user_data)
    try:
        db.add(user)
        db.commit() 
    except IntegrityError:
        db.rollback() 
        raise HTTPException(status_code=400, detail="Username or Email already exists")
    db.refresh(user)
    user_jwt = createJWT(user.id, user_data["username"])
    return {"UserAdded": user_data["username"], "JWT":user_jwt}

@router.post("/login")
def loginUser(db: db_deb, user: OAuth2PasswordRequestForm = Depends()):
    stmt = select(User).where(User.username == user.username)
    response = db.execute(stmt).scalar_one_or_none()
    if not response:
        raise HTTPException(status_code=404,detail="wrong username or password 1")
    if not verifyPass(user.password ,response.password):
        raise HTTPException(status_code=400, detail="wrong username or password 2")
    token = createJWT(response.id, response.username)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/updatePassword")
def updatePass(db: db_deb, passwords: UpdatePassword, user: Annotated[User, Depends(get_current_user)]):
    user_data = passwords.model_dump()
    if verifyPass(user_data["old_password"], user.password):  
        user.password = hashPass(user_data["new_password"])
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="Incorrect Password")
   
    return {"message": "password changed"}


