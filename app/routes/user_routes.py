
from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import  update
from typing import Annotated
from app.auth import hashPass, get_current_user, verifyJWT, oauth2_scheme
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate


router = APIRouter(
    prefix="/user",
    tags=["Users"]
)

db_dep = Annotated[Session, Depends(get_db)]


@router.get("/me")
def getCurrentUser(user: Annotated[User ,Depends(get_current_user)]):
    return {"user": UserOut.model_validate(user)}

@router.patch('/update')
def updateUser(user_info: UserUpdate, db: db_dep, jwt: Annotated[str, Depends(oauth2_scheme)]):
    try:
        user_id = verifyJWT(jwt)["id"]
        user_data = user_info.model_dump(exclude_unset=True)
        stmt = update(User).where(User.id==user_id).values(user_data)
        db.execute(stmt)
        db.commit()
        return {"Updated": user_id}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Message")
        
 



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
