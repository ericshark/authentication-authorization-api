from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Annotated
from database import get_db
from models import User
from schemas import UserCreate, UserOut

router = APIRouter(
    prefix= "/auth",
    tags = ["Auth"]
)

db_deb = Annotated[Session, Depends(get_db)]

@router.post('/')
def authenticateUser(db : db_deb ):
    pass
