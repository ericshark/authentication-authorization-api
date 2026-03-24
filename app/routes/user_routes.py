from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from typing import Annotated
from database import get_db
from models import User
from schemas import UserCreate, UserOut



router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

db_dep = Annotated[Session, Depends(get_db)]



@router.get('/app')
def returnUsers(db: db_dep):
    stmt = select(User)
    users = db.execute(stmt).scalars().all()
    return users

@router.post('/updateName')
def updateName(db: db_dep, name : str, user_id : int):
    stmt = select(User).where(User.id == user_id)
    result = db.execute(stmt).scalar_one() 
    result.name = name
    db.commit()
    
    return {'Updated':user_id, "Name": name}

@router.get('/getUser/{user_id}', response_model=UserOut)
def getUser(db: db_dep, user_id: int):
    stmt = select(User).where(User.id == user_id)
    response = db.execute(stmt).scalar_one()
    return response

@router.post('/createUser', response_model=UserOut)
def createUser2(db : db_dep, user : UserCreate):
    user_data = user.model_dump()
    new_User = User(**user_data)
    db.add(new_User)
    db.commit()
    db.refresh(new_User)
    return new_User

@router.patch('/update/{user_id}', response_model=UserOut)
def updateName2(db: db_dep, user_id : int, name: str):
    pass


@router.put('update-user/{user_id}')
def updateUser(db: db_dep, updated_user: UserCreate, user_id: int):
    stmt = update(User).where(User.id == user_id).values(**updated_user.model_dump()).returning(User)
    result = db.execute(stmt)
    db.commit()
    return result.scalar_one()
    
    
    
