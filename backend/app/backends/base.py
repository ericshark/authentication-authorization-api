from abc import ABC, abstractmethod

from fastapi import Request, Response
from redis import Redis
from sqlalchemy.orm import Session

from app.models import User


class AuthBackend(ABC):
    @staticmethod
    @abstractmethod
    def registered(
        db: Session, user: User, response: Response, redis: Redis, request: Request
    ): ...

    @staticmethod
    @abstractmethod
    def authenticate_request(db: Session, request: Request, redis: Redis) -> User: ...

    @staticmethod
    @abstractmethod
    def logout(
        response: Response, request: Request, db: Session, user: User, redis: Redis
    ): ...

    @staticmethod
    @abstractmethod
    def logout_all(
        response: Response, request: Request, db: Session, user: User, redis: Redis
    ): ...

    @staticmethod
    @abstractmethod
    def delete_user(
        response: Response, request: Request, db: Session, user: User, redis: Redis
    ): ...
