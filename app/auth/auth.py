from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.utils import get_auth_backend
from app.core.database import get_db
from app.models import RoleEnum, User


ph = PasswordHasher()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

auth_strat = get_auth_backend()


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    return auth_strat.authenticate_request(db, token)


class RoleChecker:
    def __init__(self, allowed: list[RoleEnum]):
        self.allowed = allowed

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role in self.allowed:
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
