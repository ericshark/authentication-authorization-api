from ctypes import sizeof
from datetime import datetime, timedelta, timezone
import os
from fastapi import HTTPException
from jose import ExpiredSignatureError, JWTError, jwt
from dotenv import load_dotenv
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from passlib import exc

ph = PasswordHasher()
#print(secrets.token_hex(32))

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

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
    print(result)
    return result


def verifyJWT(user_jwt: str):
    try:
        return jwt.decode(user_jwt, SECRET_KEY, algorithms=["HS256"])
    except ExpiredSignatureError as e:
        raise HTTPException(status_code=404, detail="expired JWT")
    except JWTError as e:
        print("hello")
        raise HTTPException(status_code=404, detail="jwterror")

    

    