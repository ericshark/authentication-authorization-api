from datetime import datetime, timedelta, timezone
import hashlib

from fastapi import HTTPException, Response
from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY


def create_jwt(user_id: int, username: str) -> str:
    payload = {
        "id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=0.5),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )


def set_jwt_cookie(response: Response, jwt_token: str):
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        samesite="strict",
        max_age=60 * 30,  # 30 min
    )


def refresh_hash(refresh_token: str):
    return hashlib.sha256(refresh_token.encode()).hexdigest()
