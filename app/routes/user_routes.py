from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import  update
from typing import Annotated
from app.auth import hashPass, verifyJWT, oauth2_scheme, getUser
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate



router = APIRouter(
    prefix="/user",
    tags=["Users"]
)

db_dep = Annotated[Session, Depends(get_db)]


@router.get("/me")
def getCurrentUser(db: db_dep, user: Annotated[User ,Depends(getUser)]):
    return {"user": UserOut.model_validate(user)}
  
@router.patch('/update/{user_id}')
def updateUser(db: db_dep, user_updated: UserUpdate, jwt: Annotated[str ,Depends(oauth2_scheme)]):
    user_data = user_updated.model_dump(exclude_unset=True)
    payload = verifyJWT(jwt)
    user_id = int(payload.get("id"))
    stmt = update(User).where(User.id == user_id).values(user_data)
    db.execute(stmt)
    db.commit()
    return user_data
    
@router.put('/replace/{user_id}', response_model=UserOut)
def replaceUser(db: db_dep, updated_user: UserCreate, user_id: int):
    user_data = updated_user.model_dump()
    user_data["password"] = hashPass(user_data.get("password"))
    stmt = update(User).where(User.id == user_id).values(user_data).returning(User)
    result = db.execute(stmt).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    db.commit()
    return result
