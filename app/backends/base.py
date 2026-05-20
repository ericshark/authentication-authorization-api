from abc import ABC, abstractmethod

from fastapi import Request, Response
from redis import Redis
from sqlalchemy.orm import Session

from app.models import User


class AuthBackend(ABC):
    @abstractmethod
    def registered(db: Session, user: User, response: Response, redis: Redis): ...

    @abstractmethod
    def authenticate_request(db: Session, token: str, redis: Redis) -> User: ...

    @abstractmethod
    def logout(
        response: Response, request: Request, db: Session, user: User, redis: Redis
    ): ...

    @abstractmethod
    def logout_all(
        response: Response, request: Request, db: Session, user: User, redis: Redis
    ): ...
