from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Annotated
from database import get_db
from models import User



router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

db_dep = Annotated[Session, Depends(get_db)]



@router.get('/app')
def returnUser(db: db_dep):
    stmt = select(User)
    users = db.execute(stmt).scalars().all()
    return users

    