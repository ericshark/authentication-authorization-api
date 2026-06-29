import secrets

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.auth.request_info import get_device_name, get_ip_address
from app.auth.tokens import create_jwt, hash_token
from app.core.config import settings
from app.models import TOKEN_EXPIRY_SECONDS, RefreshToken, User

SECRET_KEY = settings.SECRET_KEY


def set_refresh(
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
    hashed_token = hash_token(refresh_token)
    device_name = get_device_name(request)
    ip_address = get_ip_address(request)
    if not family_id:
        family_id = secrets.token_hex(16)
    user_refresh = RefreshToken(
        user_id=user.id,
        hashed_token=hashed_token,
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


def set_session_cookie(response: Response, user: User, session_id: str):
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="strict",
        secure=settings.is_production,
        max_age=TOKEN_EXPIRY_SECONDS,
    )
