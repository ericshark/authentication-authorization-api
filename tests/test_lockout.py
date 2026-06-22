from sqlalchemy import select

from app.auth.lockout import RATE_LIMIT_MAX_REQUESTS
from app.models import RoleEnum, User

REGISTER_PAYLOAD = {
    "username": "john",
    "name": "John Doe",
    "password": "secret123",
    "email": "john@example.com",
}


# ---------------------------------------------------------------------------
# Login brute-force lockout
# ---------------------------------------------------------------------------
def test_login_locks_out_after_max_failed_attempts(client, use_jwt):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    client.cookies.clear()

    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        resp = client.post(
            "/auth/login", data={"username": "john", "password": "wrongpass"}
        )
        assert resp.status_code == 400

    resp = client.post(
        "/auth/login", data={"username": "john", "password": "wrongpass"}
    )
    assert resp.status_code == 429


def test_login_lockout_blocks_even_correct_password(client, use_jwt, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    client.cookies.clear()
    redis_client.set("failed:john", RATE_LIMIT_MAX_REQUESTS)

    resp = client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )

    assert resp.status_code == 429


def test_successful_login_resets_failed_counter(client, use_jwt, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    client.cookies.clear()

    # Two failed attempts, then a successful one clears the counter.
    for _ in range(2):
        client.post("/auth/login", data={"username": "john", "password": "wrongpass"})
    assert redis_client.get("failed:john") is not None

    resp = client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )
    assert resp.status_code == 200
    assert redis_client.get("failed:john") is None


def test_admin_unlock_clears_lockout(client, use_jwt, db, redis_client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    user.role = RoleEnum.ADMIN
    db.commit()
    redis_client.set("failed:jane", RATE_LIMIT_MAX_REQUESTS)

    resp = client.post("/admin/unlock/jane")

    assert resp.status_code == 200
    assert redis_client.get("failed:jane") is None


# ---------------------------------------------------------------------------
# Inactive account login
# ---------------------------------------------------------------------------
def test_login_rejects_inactive_account(client, use_jwt, db):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    user.is_active = False
    db.commit()
    client.cookies.clear()

    resp = client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )

    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Role-based access control
# ---------------------------------------------------------------------------
def test_regular_user_forbidden_from_admin_route(jwt_client):
    resp = jwt_client.get("/admin/users")

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Insufficient permissions"


def test_regular_user_forbidden_from_role_change(jwt_client, db):
    user = db.execute(select(User).where(User.username == "john")).scalar_one()

    resp = jwt_client.patch(f"/admin/{user.id}/role", json={"role": "admin"})

    assert resp.status_code == 403


def test_moderator_forbidden_from_admin_only_route(jwt_client, db):
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    user.role = RoleEnum.MODERATOR
    db.commit()

    resp = jwt_client.get("/admin/users")

    assert resp.status_code == 403


def test_unauthenticated_user_rejected_from_admin_route(client, use_jwt):
    resp = client.get("/admin/users")

    assert resp.status_code == 401
