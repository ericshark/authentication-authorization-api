from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
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

@router.get('/app/{user_id}', response_model=UserOut)
def returnUser(db: db_dep, user_id : int):
    stmt = select(User).where(User.id == user_id)
    result= db.execute(stmt).scalar()
    return result

@router.post('/create')
def createUser(db : db_dep, user : UserCreate):
    user_data = user.model_dump()
    new_user = User(**user_data)
    db.add(new_user)
    db.commit()
    
    return {"UserAdded": user_data}

@router.post('/updateName')
def updateName(db: db_dep, name : str, user_id : int):
    stmt = select(User).where(User.id == user_id)
    result = db.execute(stmt).scalar()
    if result is None:
        raise HTTPException(status_code=404)
    
    result.name = name
    db.commit()
    
    return {'Updated':user_id, "Name": name}
    

@router.patch('/update/{id}', response_model=UserOut)
def updateName2(db: db_dep, user_id : int, name: str):
    pass

    