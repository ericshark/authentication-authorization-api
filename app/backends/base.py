from abc import ABC, abstractmethod

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Response
from sqlalchemy.orm import Session

from app.models import User


class AuthBackend(ABC):
    @abstractmethod
    def registered(user: User, response: Response): ...

    @abstractmethod
    def authenticate_request(db: Session, token: str) -> User: ...

    @abstractmethod
    def logout(response: Response, db: Session, user: User): ...
