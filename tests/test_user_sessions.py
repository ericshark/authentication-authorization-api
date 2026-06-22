from sqlalchemy import select

from app.auth.tokens import hash_token
from app.models import RefreshToken, UserSession

REGISTER_PAYLOAD = {
    "username": "john",
    "name": "John Doe",
    "password": "secret123",
    "email": "john@example.com",
}

SECOND_USER_PAYLOAD = {
    "username": "jane",
    "name": "Jane Doe",
    "password": "secret123",
    "email": "jane@example.com",
}


# ---------------------------------------------------------------------------
# GET /users/me/sessions
# ---------------------------------------------------------------------------
def test_get_sessions_lists_active_jwt(jwt_refresh_client):
    response = jwt_refresh_client.get("/users/me/sessions")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert {"user_id", "ip_address", "device_name", "expires_at"} <= data[0].keys()


def test_get_sessions_lists_active_session(session_client):
    response = session_client.get("/users/me/sessions")

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_get_sessions_excludes_invalid(jwt_refresh_client, db):
    db.execute(RefreshToken.__table__.update().values(valid=False))
    db.commit()

    response = jwt_refresh_client.get("/users/me/sessions")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# DELETE /users/me/sessions/{id}
# ---------------------------------------------------------------------------
def test_delete_session_revokes_only_target_jwt(jwt_refresh_client, db):
    # The fixture leaves two valid refresh tokens (one from register, one from
    # login); the login token is the one currently in the cookie jar.
    current = hash_token(jwt_refresh_client.cookies.get("refresh_token"))
    tokens = db.execute(select(RefreshToken).where(RefreshToken.valid)).scalars().all()
    assert len(tokens) == 2
    target = next(t for t in tokens if t.hashed_token != current)

    response = jwt_refresh_client.delete(f"/users/me/sessions/{target.hashed_token}")

    assert response.status_code == 200
    db.expire_all()
    assert db.get(RefreshToken, target.id).valid is False
    # The current session is untouched and can still refresh.
    assert jwt_refresh_client.get("/auth/refresh").status_code == 200


def test_delete_session_revokes_target_session_backend(
    client, use_session, db, redis_client
):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    session_a = client.cookies.get("session_id")
    client.cookies.clear()
    client.post("/auth/login", data={"username": "john", "password": "secret123"})

    response = client.delete(f"/users/me/sessions/{session_a}")

    assert response.status_code == 200
    # Current session still works.
    assert client.get("/users/me").status_code == 200

    db.expire_all()
    revoked = db.execute(
        select(UserSession).where(UserSession.session_id == session_a)
    ).scalar_one()
    assert revoked.valid is False
    # The Redis cache for the revoked session was cleared, so it no longer authenticates.
    assert redis_client.get(f"session:{session_a}") is None
    client.cookies.clear()
    client.cookies.set("session_id", session_a)
    assert client.get("/users/me").status_code == 401


def test_delete_session_unknown_id_is_noop(jwt_refresh_client, db):
    response = jwt_refresh_client.delete("/users/me/sessions/does-not-exist")

    assert response.status_code == 200
    valid = db.execute(select(RefreshToken).where(RefreshToken.valid)).scalars().all()
    assert len(valid) == 2


# ---------------------------------------------------------------------------
# DELETE /users/me/sessions
# ---------------------------------------------------------------------------
def test_delete_all_sessions_keeps_current_jwt(jwt_refresh_client, db):
    current = hash_token(jwt_refresh_client.cookies.get("refresh_token"))

    response = jwt_refresh_client.delete("/users/me/sessions")

    assert response.status_code == 200
    db.expire_all()
    for token in db.execute(select(RefreshToken)).scalars().all():
        assert token.valid is (token.hashed_token == current)
    assert jwt_refresh_client.get("/auth/refresh").status_code == 200


def test_delete_all_sessions_keeps_current_session_backend(
    client, use_session, db, redis_client
):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    session_a = client.cookies.get("session_id")
    client.cookies.clear()
    client.post("/auth/login", data={"username": "john", "password": "secret123"})
    session_b = client.cookies.get("session_id")

    response = client.delete("/users/me/sessions")

    assert response.status_code == 200
    # Current session survives.
    client.cookies.clear()
    client.cookies.set("session_id", session_b)
    assert client.get("/users/me").status_code == 200
    # The other session is revoked in the DB and evicted from Redis.
    assert redis_client.get(f"session:{session_a}") is None
    client.cookies.clear()
    client.cookies.set("session_id", session_a)
    assert client.get("/users/me").status_code == 401


# ---------------------------------------------------------------------------
# PATCH /users/update-me  (conflict path)
# ---------------------------------------------------------------------------
def test_update_me_duplicate_email_conflicts(client, use_jwt):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    client.cookies.clear()
    client.post("/auth/register", json=SECOND_USER_PAYLOAD)  # current user = jane

    response = client.patch(
        "/users/update-me", json={"email": REGISTER_PAYLOAD["email"]}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already taken"
