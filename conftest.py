from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.database import get_db
from app.models import  Base
from app.main import app
import pytest

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(bind=engine)


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
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def auth_client(client):  # depends on client fixture
    # register a user
    client.post("/auth/createUser", json={
        "username": "john",
        "name":"bob",
        "password": "secret123",
        "email": "john@example.com"
    })
    # log in and get token
    response = client.post("/auth/login", data={
        "username": "john",
        "password": "secret123"
    })
    token = response.json()["access_token"]

    # attach token to every subsequent request
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client