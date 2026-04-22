from typing import Annotated, override

from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.backends.base import AuthBackend
from app.database import get_db


db_dep = Annotated[Session, Depends(get_db)]


class JWTBackend(AuthBackend):
    def __init__(self, form):
        pass

    @override
    def login(db: db_dep, form: OAuth2PasswordRequestForm = Depends()):
        pass

    @override
    def logout():
        # JWT is stateless so not valid method
        pass

    @override
    def authenticate_request():
        pass
