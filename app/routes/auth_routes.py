from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from typing import Annotated
from database import get_db
from models import User
from schemas import UpdatePassword, UserCreate, UserOut, loginUser, jwtLogin
from auth import hashPass, createJWT, verifyPass
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

router = APIRouter(
    prefix= "/login",
    tags = ["Auth"]
)

db_deb = Annotated[Session, Depends(get_db)]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl= "token")

@router.get("/items")
async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}
    


@router.post('/createUser', )
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
def loginUser(db: db_deb, user: loginUser):
    user = user.model_dump()
    stmt = select(User).where(User.username == user["username"])
    response = db.execute(stmt).scalar_one_or_none()
    if not response:
        raise HTTPException(status_code=404,detail="not found user")
    if not verifyPass(user["password"] ,response.password):
        raise HTTPException(status_code=400, detail="Wrong password")
    userJWT = createJWT(response.id, response.username)
    db.commit()
    return {"UserLogin": "Succesfull", "JWT": userJWT}


@router.post("/updatePassword")
def updatePass(db: db_deb, passwords: UpdatePassword):
    pass