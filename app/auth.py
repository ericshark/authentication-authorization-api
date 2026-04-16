import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, VerifyMismatchError
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import RoleEnum

ph = PasswordHasher()
# print(secrets.token_hex(32))

load_dotenv()
# Force it to be a string, even if empty
SECRET_KEY = str(os.getenv("SECRET_KEY", "default_secret_key"))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hashPass(password: str):
    result = ph.hash(password)
    return result


def verifyPass(plain: str, hashed: str):
    try:
        ph.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False
    except Argon2Error as e:
        print("Unknown Error: ", e)
        return False


def createJWT(id: int, username: str):
    payload = {
        "id": str(id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    result = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return result


def verifyJWT(user_jwt: str):
    try:
        return jwt.decode(user_jwt, SECRET_KEY, algorithms=["HS256"])
    except ExpiredSignatureError:
        raise HTTPException(status_code=404, detail="expired JWT")
    except JWTError:
        raise HTTPException(status_code=404, detail="jwterror")


def get_current_user(
    jwt: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]
):
    try:
        user = db.get(User, verifyJWT(jwt)["id"])
    except HTTPException as e:
        print(e)
        raise e
    except SQLAlchemyError as e:
        print(e)
        raise e
    return user


def require_role(role: RoleEnum):
    pass
