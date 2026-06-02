from unittest.mock import MagicMock, patch

import resend
from sqlalchemy import select

from app.models import User
from app.services import email_service

REGISTER_PAYLOAD = {
    "username": "john",
    "name": "John Doe",
    "password": "secret123",
    "email": "john@example.com",
}


# --- GET /auth/verify-user ---


def test_request_verification_returns_success(jwt_client):
    with patch("app.routes.auth_routes.send_verification_email_task") as mock_task:
        mock_task.delay = MagicMock()
        response = jwt_client.get("/auth/verify-user")
    assert response.status_code == 200
    assert response.json() == {"message": "Verification email sent"}


def test_request_verification_stores_token_in_redis(jwt_client, redis_client):
    with patch("app.routes.auth_routes.send_verification_email_task") as mock_task:
        mock_task.delay = MagicMock()
        jwt_client.get("/auth/verify-user")
    assert len(redis_client.keys("verify:*")) == 1


def test_request_verification_dispatches_task_with_correct_args(jwt_client):
    with patch("app.routes.auth_routes.send_verification_email_task") as mock_task:
        mock_task.delay = MagicMock()
        jwt_client.get("/auth/verify-user")
    mock_task.delay.assert_called_once()
    email_arg, _, token_arg = mock_task.delay.call_args.args
    assert email_arg == "john@example.com"
    assert len(token_arg) == 64  # secrets.token_hex(32) produces 64 hex chars


def test_request_verification_rejects_already_verified(jwt_client, db):
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    user.is_verified = True
    db.commit()
    response = jwt_client.get("/auth/verify-user")
    assert response.status_code == 400


def test_request_verification_requires_auth(client, use_jwt):
    response = client.get("/auth/verify-user")
    assert response.status_code == 401


def test_request_verification_rate_limit(jwt_client):
    with patch("app.routes.auth_routes.send_verification_email_task") as mock_task:
        mock_task.delay = MagicMock()
        for _ in range(3):
            assert jwt_client.get("/auth/verify-user").status_code == 200
        assert jwt_client.get("/auth/verify-user").status_code == 429


# --- GET /auth/verify-email ---


def test_verify_email_success(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testverifytoken"
    redis_client.set(f"verify:{token}", str(user.id))

    response = client.get(f"/auth/verify-email?token={token}")
    assert response.status_code == 200
    assert response.json() == {"message": "Email verified successfully"}
    db.refresh(user)
    assert user.is_verified is True


def test_verify_email_deletes_token_after_use(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testverifytoken"
    redis_client.set(f"verify:{token}", str(user.id))

    client.get(f"/auth/verify-email?token={token}")
    assert redis_client.get(f"verify:{token}") is None


def test_verify_email_one_time_use(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testverifytoken"
    redis_client.set(f"verify:{token}", str(user.id))

    client.get(f"/auth/verify-email?token={token}")
    response = client.get(f"/auth/verify-email?token={token}")
    assert response.status_code == 400


def test_verify_email_invalid_token(client, use_jwt):
    response = client.get("/auth/verify-email?token=badtoken")
    assert response.status_code == 400


# --- email_service.send_verification_email ---


def test_send_verification_email_calls_resend(monkeypatch):
    sent = {}

    monkeypatch.setattr(resend.Emails, "send", lambda params: sent.update(params) or {"id": "x"})
    monkeypatch.setattr("app.core.config.settings.APP_BASE_URL", "http://testserver")

    email_service.send_verification_email("user@example.com", "testuser", "tok123")

    assert sent["to"] == "user@example.com"
    assert sent["subject"] == "Verify your email address"
    assert "tok123" in sent["html"]
    assert "testuser" in sent["html"]
