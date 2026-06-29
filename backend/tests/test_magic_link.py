from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.models import User

REGISTER_PAYLOAD = {
    "username": "john",
    "name": "John Doe",
    "password": "secret123",
    "email": "john@example.com",
}


# --- POST /auth/magic-link ---


def test_request_magic_link_returns_success_for_registered_email(client, use_jwt):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    with patch("app.routes.auth_routes.send_magic_link_task") as mock_task:
        mock_task.delay = MagicMock()
        response = client.post("/auth/magic-link", json={"email": "john@example.com"})
    assert response.status_code == 200


def test_request_magic_link_returns_same_response_for_unknown_email(client, use_jwt):
    response = client.post("/auth/magic-link", json={"email": "nobody@example.com"})
    assert response.status_code == 200


def test_request_magic_link_dispatches_task_for_registered_user(client, use_jwt):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    with patch("app.routes.auth_routes.send_magic_link_task") as mock_task:
        mock_task.delay = MagicMock()
        client.post("/auth/magic-link", json={"email": "john@example.com"})
    mock_task.delay.assert_called_once()


def test_request_magic_link_does_not_dispatch_task_for_unknown_email(client, use_jwt):
    with patch("app.routes.auth_routes.send_magic_link_task") as mock_task:
        mock_task.delay = MagicMock()
        client.post("/auth/magic-link", json={"email": "nobody@example.com"})
    mock_task.delay.assert_not_called()


def test_request_magic_link_stores_token_in_redis(client, use_jwt, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    with patch("app.routes.auth_routes.send_magic_link_task") as mock_task:
        mock_task.delay = MagicMock()
        client.post("/auth/magic-link", json={"email": "john@example.com"})
    assert len(redis_client.keys("magic:*")) == 1


def test_request_magic_link_rate_limit(client, use_jwt):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    with patch("app.routes.auth_routes.send_magic_link_task") as mock_task:
        mock_task.delay = MagicMock()
        for _ in range(3):
            assert client.post("/auth/magic-link", json={"email": "john@example.com"}).status_code == 200
        response = client.post("/auth/magic-link", json={"email": "john@example.com"})
    assert response.status_code == 429


# --- GET /auth/magic-link/verify ---


def test_verify_magic_link_sets_jwt_cookie(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testmagictoken"
    redis_client.set(f"magic:{token}", str(user.id))

    response = client.get(f"/auth/magic-link/verify?token={token}")
    assert response.status_code == 200
    assert "access_token" in response.cookies


def test_verify_magic_link_sets_session_cookie(client, use_session, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testmagictoken"
    redis_client.set(f"magic:{token}", str(user.id))

    response = client.get(f"/auth/magic-link/verify?token={token}")
    assert response.status_code == 200
    assert "session_id" in response.cookies


def test_verify_magic_link_grants_access_to_protected_route(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    client.cookies.clear()

    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testmagictoken"
    redis_client.set(f"magic:{token}", str(user.id))

    client.get(f"/auth/magic-link/verify?token={token}")
    response = client.get("/users/me")
    assert response.status_code == 200
    assert response.json()["username"] == "john"


def test_verify_magic_link_invalid_token(client, use_jwt):
    response = client.get("/auth/magic-link/verify?token=badtoken")
    assert response.status_code == 400


def test_verify_magic_link_one_time_use(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testmagictoken"
    redis_client.set(f"magic:{token}", str(user.id))

    client.get(f"/auth/magic-link/verify?token={token}")
    response = client.get(f"/auth/magic-link/verify?token={token}")
    assert response.status_code == 400


def test_verify_magic_link_deletes_token(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    token = "testmagictoken"
    redis_client.set(f"magic:{token}", str(user.id))

    client.get(f"/auth/magic-link/verify?token={token}")
    assert redis_client.get(f"magic:{token}") is None
