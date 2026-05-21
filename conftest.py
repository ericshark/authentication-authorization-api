import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.utils import get_auth_backend
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app
from app.models import Base

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db, redis_client):

    def override_get_db():
        yield db

    def override_get_redis():
        return redis_client

    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def use_jwt(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_STRATEGY", "JWT")
    monkeypatch.setattr(settings, "REFRESH_TOKENS_ENABLED", False)
    monkeypatch.setattr(settings, "is_production", False)
    get_auth_backend.cache_clear()
    yield
    get_auth_backend.cache_clear()


@pytest.fixture
def use_session(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_STRATEGY", "SESSION")
    monkeypatch.setattr(settings, "is_production", False)
    get_auth_backend.cache_clear()
    yield
    get_auth_backend.cache_clear()


@pytest.fixture
def use_jwt_with_refresh(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_STRATEGY", "JWT")
    monkeypatch.setattr(settings, "REFRESH_TOKENS_ENABLED", True)
    monkeypatch.setattr(settings, "is_production", False)
    get_auth_backend.cache_clear()
    yield
    get_auth_backend.cache_clear()


@pytest.fixture
def jwt_client(client, use_jwt):
    client.post(
        "/auth/register",
        json={
            "username": "john",
            "name": "bob",
            "password": "secret123",
            "email": "john@example.com",
        },
    )
    return client


@pytest.fixture
def session_client(client, use_session):
    client.post(
        "/auth/register",
        json={
            "username": "john",
            "name": "bob",
            "password": "secret123",
            "email": "john@example.com",
        },
    )
    return client


@pytest.fixture
def jwt_refresh_client(client, use_jwt_with_refresh):
    client.post(
        "/auth/register",
        json={
            "username": "john",
            "name": "bob",
            "password": "secret123",
            "email": "john@example.com",
        },
    )
    client.cookies.clear()
    client.post("/auth/login", data={"username": "john", "password": "secret123"})
    return client
