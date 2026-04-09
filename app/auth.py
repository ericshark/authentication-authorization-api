
from datetime import datetime, timedelta, timezone
import os
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from dotenv import load_dotenv
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import RoleEnum


ph = PasswordHasher()
#print(secrets.token_hex(32))

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl= "/login/user")

def hashPass(password: str):
    result = ph.hash(password)
    return result

def verifyPass(plain: str, hashed: str):
    try:
        ph.verify(hashed, plain) 
        return True
    except VerifyMismatchError:
        return False
    except:
        return False

def createJWT(id: int, username: str):
    payload = {
        "id": str(id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours = 1)
    }
    
    result = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return result


def verifyJWT(user_jwt: str):
    try:
        return jwt.decode(user_jwt, SECRET_KEY, algorithms=["HS256"])
    except ExpiredSignatureError as e:
        raise HTTPException(status_code=404, detail="expired JWT")
    except JWTError as e:
        raise HTTPException(status_code=404, detail="jwterror")


def get_current_user(jwt: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session,Depends(get_db)]):
    try:
        user = db.get(User, verifyJWT(jwt)["id"])
    except HTTPException as e:
        raise e
    except:
        raise HTTPException(status_code=401, detail="User not found")
    return user
            
def require_role(role: RoleEnum):
    pass