from fastapi import APIRouter, Depends, HTTPException
from passlib import exc
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from typing import Annotated
from database import get_db
from models import User
from schemas import UpdatePassword, UserCreate, UserOut, loginUser
from auth import hashPass, createJWT, verifyPass, verifyJWT
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

router = APIRouter(
    prefix= "/login",
    tags = ["Auth"]
)

db_deb = Annotated[Session, Depends(get_db)]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl= "/login/user")




@router.post('/createUser' )
def createUser(db: db_deb, new_user: UserCreate):
    user_data = new_user.model_dump()
    user_data["password"] = hashPass(user_data["password"])
    
    user = User(**user_data)
    try:
        db.add(user)
        db.commit() 
    except IntegrityError:
        db.rollback() # VERY IMPORTANT
        raise HTTPException(status_code=400, detail="Username or Email already exists")
    db.refresh(user)
    user_jwt = createJWT(user.id, user_data["username"])
    return {"UserAdded": user_data["username"], "JWT":user_jwt}

@router.post("/user")
def loginUser(db: db_deb, user: OAuth2PasswordRequestForm = Depends()):
    stmt = select(User).where(User.username == user.username)
    response = db.execute(stmt).scalar_one_or_none()
    if not response:
        raise HTTPException(status_code=404,detail="not found user")
    if not verifyPass(user.password ,response.password):
        raise HTTPException(status_code=400, detail="Wrong password")
    token = createJWT(response.id, response.username)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/updatePassword")
def updatePass(db: db_deb, passwords: UpdatePassword):
    user_data = passwords.model_dump()
    try:
        stmt = select(User).where(User.username==user_data["username"])
        user = db.execute(stmt).scalar_one()
        if verifyPass(user_data["old_password"], user.password ):
            user.password = hashPass(user_data["new_password"])
            db.commit()
        else:
            raise HTTPException(status_code=400, detail="Incorrect Password")
    except NoResultFound:
        db.rollback()
        raise HTTPException(status_code=404, detail="Username Not found")
    return {"message": "password changed"}



#eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjMiLCJ1c2VybmFtZSI6ImVyaWMiLCJleHAiOjE3NzQ2MjQ5NTF9.99fOv5DNa1NtBwiFbdLIVx02RkhLzGA7C2BZw1DA3FM
 
@router.post("/getCurrentUser")
def getCurrentUser(db: db_deb, jwt: Annotated[str ,Depends(oauth2_scheme)]):
    payload = verifyJWT(jwt)
    try:
        user = db.get(User, int(payload["id"]))
    except Exception as e:
        print(e)
    return {"user": UserOut.model_validate(user), "jwts": payload}
  

@router.post("/me")
def getCurrentUser(db: db_deb, jwt: Annotated[str ,Depends(oauth2_scheme)]):
    payload = verifyJWT(jwt)
    try:
        user = db.get(User, int(payload["id"]))
    except Exception as e:
        print(e)
    return {"user": UserOut.model_validate(user), "jwts": payload}
  