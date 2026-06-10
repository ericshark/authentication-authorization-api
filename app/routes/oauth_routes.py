import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.utils import get_auth_backend
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.models import SocialAccount, User
from authlib.integrations.starlette_client import OAuth, OAuthError

logger = logging.getLogger(__name__)

router = APIRouter()

db_dep = Annotated[Session, Depends(get_db)]

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google")
async def google_sign_in(
    request: Request,
):
    return await oauth.google.authorize_redirect(
        request, redirect_uri=settings.GOOGLE_CLIENT_URI
    )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: db_dep,
    response: Response,
    r: Annotated[Redis, Depends(get_redis)],
):
    try:
        token = await oauth.google.authorize_access_token(request)

        user_info = token.get("userinfo") or {}
        google_id = user_info.get("sub")
        email = user_info.get("email")
        if not google_id or not email:
            raise HTTPException(status_code=400, detail="Invalid Google user info")

        # check if social account exists
        social = db.execute(
            select(SocialAccount).where(
                SocialAccount.provider == "google",
                SocialAccount.provider_id == google_id,
            )
        ).scalar_one_or_none()

        if social:
            # existing OAuth user — get their user record
            user = db.get(User, social.user_id)
        else:
            # check if email already registered normally
            user = db.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()

            if not user:
                # brand new user — create them
                user = User(email=email, username=email.split("@")[0], password=None)
                db.add(user)
                db.flush()  # get user.id without committing

            # link social account to user
            social = SocialAccount(
                user_id=user.id,
                provider="google",
                provider_id=google_id,
            )
            db.add(social)
            db.commit()
            db.refresh(user)

        # issue your normal JWT/session
        return get_auth_backend().registered(db, user, response, r, request)
    except OAuthError:
        raise HTTPException(status_code=400, detail="OAuth authentication failed")


oauth.register(
    name="github",
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_SECRET,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    client_kwargs={"scope": "user:email"},
)


@router.get("/github")
async def github_sign_in(request: Request):
    return await oauth.github.authorize_redirect(
        request, redirect_uri=settings.GITHUB_CLIENT_URI
    )


@router.get("/github/callback")
async def github_callback(
    request: Request,
    db: db_dep,
    response: Response,
    r: Annotated[Redis, Depends(get_redis)],
):
    try:
        token = await oauth.github.authorize_access_token(request)
        resp = await oauth.github.get("https://api.github.com/user", token=token)
        user_info = resp.json()
        github_id = str(user_info["id"])
        email = user_info.get("email")
        if not email:
            email_resp = await oauth.github.get(
                "https://api.github.com/user/emails", token=token
            )
            emails = email_resp.json()
            if isinstance(emails, list):
                primary = next((e for e in emails if e.get("primary")), None)
                email = primary.get("email") if primary else None
            if not email:
                raise HTTPException(
                    status_code=400,
                    detail="Please make your GitHub email public to use this login method",
                )

        social = db.execute(
            select(SocialAccount).where(
                SocialAccount.provider == "github",
                SocialAccount.provider_id == github_id,
            )
        ).scalar_one_or_none()
        if social:
            user = db.get(User, social.user_id)
        else:
            user = db.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()
            if not user:
                user = User(email=email, username=email.split("@")[0], password=None)
                db.add(user)
                db.flush()
            social = SocialAccount(
                provider="github", provider_id=github_id, user_id=user.id
            )
            db.add(social)
            db.commit()
            db.refresh(user)
        return get_auth_backend().registered(db, user, response, r, request)
    except OAuthError:
        raise HTTPException(status_code=400, detail="OAuth authentication failed")
