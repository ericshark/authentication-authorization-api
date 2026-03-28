from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from typing import Annotated
from database import get_db
from models import User
from schemas import UpdatePassword, UserCreate, UserOut, UserUpdate


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

db_dep = Annotated[Session, Depends(get_db)]


@router.get('/getUser/{user_id}', response_model=UserOut)
def getUser(db: db_dep, user_id: int):
    stmt = select(User).where(User.id == user_id)
    response = db.execute(stmt).scalar_one()
    return response

@router.patch('/update/{user_id}', response_model=UserOut)
def updateUser(db: db_dep, user_updated: UserUpdate, user_id: int):
    user_data = user_updated.model_dump(exclude_unset=True)
    stmt = update(User).where(User.id == user_id).values(**user_data).returning(User)
    user = db.execute(stmt).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.commit()
    return user
    


@router.put('/replace/{user_id}', response_model=UserOut)
def replaceUser(db: db_dep, updated_user: UserCreate, user_id: int):
    stmt = update(User).where(User.id == user_id).values(**updated_user.model_dump()).returning(User)
    result = db.execute(stmt).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    db.commit()
    return result

    