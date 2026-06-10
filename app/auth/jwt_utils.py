import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import TOKEN_EXPIRY_SECONDS, RefreshToken, User
from user_agents import parse

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


def set_refresh_cookie(
    response: Response,
    db: Session,
    user: User,
    request: Request,
    family_id: str = None,
):
    refresh_token = secrets.token_hex(32)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        max_age=TOKEN_EXPIRY_SECONDS,
    )
    hash_token = refresh_hash(refresh_token)
    ua = parse(request.headers.get("User-Agent", ""))
    device_name = f"{ua.browser.family} on {ua.os.family}"
    ip_address = (
        request.headers.get("X-Forwarded-For")
        or (request.client.host if request.client else None)
        or "unknown"
    )
    if not family_id:
        family_id = secrets.token_hex(16)
    user_refresh = RefreshToken(
        user_id=user.id,
        hashed_token=hash_token,
        family_id=family_id,
        user_agent=request.headers.get("user-agent", "unknown"),
        ip_address=ip_address.split(",")[0].strip(),
        device_name=device_name,
    )
    db.add(user_refresh)


def set_jwt_cookie(response: Response, user: User):
    jwt_token = create_jwt(user.id, user.username)
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        max_age=60 * 30,  # 30 min
    )


def refresh_hash(refresh_token: str):
    return hashlib.sha256(refresh_token.encode()).hexdigest()
