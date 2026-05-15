import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.config import settings
from app.auth.utils import get_auth_backend
from app.main import app
import fakeredis

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis()


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

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def use_jwt(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_STRATEGY", "JWT")
    get_auth_backend.cache_clear()
    yield
    get_auth_backend.cache_clear()


@pytest.fixture
def use_session(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_STRATEGY", "SESSION")
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
    response = client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )
    token = response.cookies.get("access_token")

    client.cookies.update({"access_token": token})
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
    response = client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )
    token = response.cookies.get("session_id")
    client.cookies.update({"session_id": token})

    return client
