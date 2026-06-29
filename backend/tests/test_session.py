from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import UserSession


REGISTER_PAYLOAD = {
    "username": "john",
    "name": "John Doe",
    "password": "secret123",
    "email": "john@example.com",
}


def test_register_success(client, use_session):
    response = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 200
    assert "session_id" in response.cookies


def test_register_records_session_metadata(client, use_session, db):
    response = client.post(
        "/auth/register",
        json=REGISTER_PAYLOAD,
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
            "X-Forwarded-For": "203.0.113.10, 10.0.0.1",
        },
    )

    assert response.status_code == 200
    session = db.execute(select(UserSession)).scalar_one()
    assert session.user_agent.startswith("Mozilla/5.0")
    assert session.ip_address == "203.0.113.10"
    assert session.device_name
    assert session.last_active is not None


def test_register_duplicate_fails(client, use_session):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    response = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 400


def test_login_success(session_client):
    response = session_client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )
    assert response.status_code == 200
    assert "session_id" in response.cookies


def test_login_wrong_password(client, use_session):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/auth/login", data={"username": "john", "password": "wrongpass"}
    )
    assert response.status_code == 400


def test_login_wrong_username(client, use_session):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/auth/login", data={"username": "nobody", "password": "secret123"}
    )
    assert response.status_code == 400


def test_get_me(session_client):
    response = session_client.get("/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "john"
    assert data["email"] == "john@example.com"


def test_get_me_updates_only_current_session_last_active(
    client, use_session, db, redis_client
):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    first_session_id = client.cookies.get("session_id")
    client.cookies.clear()
    client.post("/auth/login", data={"username": "john", "password": "secret123"})
    second_session_id = client.cookies.get("session_id")

    first_last_active = datetime.now(timezone.utc) - timedelta(days=2)
    second_last_active = datetime.now(timezone.utc) - timedelta(days=1)
    first_session = db.execute(
        select(UserSession).where(UserSession.session_id == first_session_id)
    ).scalar_one()
    second_session = db.execute(
        select(UserSession).where(UserSession.session_id == second_session_id)
    ).scalar_one()
    first_session.last_active = first_last_active
    second_session.last_active = second_last_active
    db.commit()
    redis_client.delete(f"last_active:{second_session_id}")

    response = client.get("/users/me")

    assert response.status_code == 200
    db.expire_all()
    first_session = db.execute(
        select(UserSession).where(UserSession.session_id == first_session_id)
    ).scalar_one()
    second_session = db.execute(
        select(UserSession).where(UserSession.session_id == second_session_id)
    ).scalar_one()
    assert first_session.last_active.replace(tzinfo=timezone.utc) == first_last_active
    assert second_session.last_active.replace(tzinfo=timezone.utc) > second_last_active


def test_get_me_throttles_last_active_updates(client, use_session, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    session_id = client.cookies.get("session_id")
    original_last_active = datetime.now(timezone.utc) - timedelta(days=1)
    session = db.execute(
        select(UserSession).where(UserSession.session_id == session_id)
    ).scalar_one()
    session.last_active = original_last_active
    db.commit()
    redis_client.set(f"last_active:{session_id}", 1, ex=300)

    response = client.get("/users/me")

    assert response.status_code == 200
    db.expire_all()
    session = db.execute(
        select(UserSession).where(UserSession.session_id == session_id)
    ).scalar_one()
    assert session.last_active.replace(tzinfo=timezone.utc) == original_last_active


def test_unauthenticated_request(client, use_session):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_logout(session_client):
    response = session_client.get("/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "logged out"}
    # Cookie should be cleared — subsequent request is unauthenticated
    response = session_client.get("/users/me")
    assert response.status_code == 401


def test_update_password_success(session_client):
    response = session_client.patch(
        "/auth/password",
        json={"old_password": "secret123", "new_password": "newpass456"},
    )
    assert response.status_code == 200
    # New password works at login
    login = session_client.post(
        "/auth/login", data={"username": "john", "password": "newpass456"}
    )
    assert login.status_code == 200


def test_update_password_wrong_old_password(session_client):
    response = session_client.patch(
        "/auth/password",
        json={"old_password": "wrongpassword", "new_password": "newpass456"},
    )
    assert response.status_code == 400
