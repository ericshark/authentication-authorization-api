from abc import ABC, abstractmethod

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.models import User


class AuthBackend(ABC):
    @abstractmethod
    def login(self, db: Session, form: OAuth2PasswordRequestForm) -> dict: ...

    @abstractmethod
    def authenticate_request(self, db: Session) -> User: ...
