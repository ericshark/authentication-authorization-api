from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.models import User

REGISTER_PAYLOAD = {
    "username": "john",
    "name": "John Doe",
    "password": "secret123",
    "email": "john@example.com",
}


# --- POST /auth/forgot-password ---


def test_forgot_password_returns_success_for_registered_email(client, use_jwt):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    with patch("app.routes.auth_routes.send_password_reset_task") as mock_task:
        mock_task.delay = MagicMock()
        response = client.post("/auth/forgot-password", json={"email": "john@example.com"})
    assert response.status_code == 200


def test_forgot_password_returns_same_response_for_unknown_email(client, use_jwt):
    response = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert response.status_code == 200


def test_forgot_password_dispatches_task_for_registered_user(client, use_jwt):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    with patch("app.routes.auth_routes.send_password_reset_task") as mock_task:
        mock_task.delay = MagicMock()
        client.post("/auth/forgot-password", json={"email": "john@example.com"})
    mock_task.delay.assert_called_once()


def test_forgot_password_does_not_dispatch_task_for_unknown_email(client, use_jwt):
    with patch("app.routes.auth_routes.send_password_reset_task") as mock_task:
        mock_task.delay = MagicMock()
        client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    mock_task.delay.assert_not_called()


def test_forgot_password_stores_token_in_redis(client, use_jwt, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    with patch("app.routes.auth_routes.send_password_reset_task") as mock_task:
        mock_task.delay = MagicMock()
        client.post("/auth/forgot-password", json={"email": "john@example.com"})
    assert len(redis_client.keys("reset:*")) == 1


def test_forgot_password_rate_limit(client, use_jwt):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    with patch("app.routes.auth_routes.send_password_reset_task") as mock_task:
        mock_task.delay = MagicMock()
        for _ in range(3):
            assert client.post("/auth/forgot-password", json={"email": "john@example.com"}).status_code == 200
        response = client.post("/auth/forgot-password", json={"email": "john@example.com"})
    assert response.status_code == 429


# --- POST /auth/reset-password ---


def test_reset_password_success(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testresettoken"
    redis_client.set(f"reset:{token}", str(user.id))

    response = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "newpassword123"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Password reset successfully"}


def test_reset_password_new_password_works_at_login(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testresettoken"
    redis_client.set(f"reset:{token}", str(user.id))

    client.post("/auth/reset-password", json={"token": token, "new_password": "newpassword123"})

    client.cookies.clear()
    login = client.post("/auth/login", data={"username": "john", "password": "newpassword123"})
    assert login.status_code == 200


def test_reset_password_old_password_no_longer_works(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testresettoken"
    redis_client.set(f"reset:{token}", str(user.id))

    client.post("/auth/reset-password", json={"token": token, "new_password": "newpassword123"})

    client.cookies.clear()
    login = client.post("/auth/login", data={"username": "john", "password": "secret123"})
    assert login.status_code == 400


def test_reset_password_invalid_token(client, use_jwt):
    response = client.post(
        "/auth/reset-password",
        json={"token": "badtoken", "new_password": "newpassword123"},
    )
    assert response.status_code == 400


def test_reset_password_one_time_use(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testresettoken"
    redis_client.set(f"reset:{token}", str(user.id))

    client.post("/auth/reset-password", json={"token": token, "new_password": "newpassword123"})
    response = client.post("/auth/reset-password", json={"token": token, "new_password": "anotherpass456"})
    assert response.status_code == 400


def test_reset_password_deletes_token(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testresettoken"
    redis_client.set(f"reset:{token}", str(user.id))

    client.post("/auth/reset-password", json={"token": token, "new_password": "newpassword123"})
    assert redis_client.get(f"reset:{token}") is None
