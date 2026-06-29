import pyotp
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.auth.lockout import RATE_LIMIT_MAX_REQUESTS
from app.auth.tokens import hash_token
from app.auth.totp import decrypt_secret
from app.core.config import settings
from app.models import User


REGISTER_PAYLOAD = {
    "username": "john",
    "name": "John Doe",
    "password": "secret123",
    "email": "john@example.com",
}


def enable_totp(monkeypatch):
    monkeypatch.setattr(settings, "TOTP", True)
    monkeypatch.setattr(settings, "TOTP_SECRET", Fernet.generate_key().decode())


# ---------------------------------------------------------------------------
# /2fa/setup
# ---------------------------------------------------------------------------
def test_2fa_setup_returns_qr_and_secret(client, use_jwt, db, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)

    resp = client.post("/auth/2fa/setup")

    assert resp.status_code == 200
    data = resp.json()
    assert "qr_code" in data
    assert data["qr_code"].startswith("data:image/png;base64,")
    assert "secret" in data


def test_2fa_setup_encrypts_secret_in_db(client, use_jwt, db, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)

    secret = client.post("/auth/2fa/setup").json()["secret"]

    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    assert user.totp_secret != secret
    assert decrypt_secret(user.totp_secret) == secret


def test_2fa_setup_requires_auth(client, use_jwt, monkeypatch):
    enable_totp(monkeypatch)

    resp = client.post("/auth/2fa/setup")

    assert resp.status_code == 401


def test_2fa_setup_404_when_totp_disabled(client, use_jwt, db, monkeypatch):
    monkeypatch.setattr(settings, "TOTP", False)
    client.post("/auth/register", json=REGISTER_PAYLOAD)

    resp = client.post("/auth/2fa/setup")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /2fa/confirm
# ---------------------------------------------------------------------------
def test_2fa_confirm_valid_code(client, use_jwt, db, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    secret = client.post("/auth/2fa/setup").json()["secret"]

    resp = client.post(
        "/auth/2fa/confirm",
        json={"secret_token": pyotp.TOTP(secret).now()},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "successful 2fa"
    assert len(data["backup_codes"]) == 10
    db.expire_all()
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    assert user.totp_enabled is True
    assert len(user.backup_codes) == 10


def test_2fa_confirm_invalid_code(client, use_jwt, db, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    client.post("/auth/2fa/setup")

    resp = client.post(
        "/auth/2fa/confirm",
        json={"secret_token": "000000"},
    )

    assert resp.status_code == 401


def test_2fa_confirm_stores_hashed_backup_codes(client, use_jwt, db, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    secret = client.post("/auth/2fa/setup").json()["secret"]

    resp = client.post(
        "/auth/2fa/confirm",
        json={"secret_token": pyotp.TOTP(secret).now()},
    )

    raw_codes = resp.json()["backup_codes"]
    db.expire_all()
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    for raw in raw_codes:
        assert hash_token(raw) in user.backup_codes


# ---------------------------------------------------------------------------
# /2fa/verify — full flow
# ---------------------------------------------------------------------------
def test_2fa_full_flow_with_totp(client, use_jwt, db, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    secret = client.post("/auth/2fa/setup").json()["secret"]
    client.post(
        "/auth/2fa/confirm",
        json={"secret_token": pyotp.TOTP(secret).now()},
    )

    client.cookies.clear()
    login_data = client.post(
        "/auth/login",
        data={"username": "john", "password": "secret123"},
    ).json()

    assert login_data["requires_2fa"] is True

    resp = client.post(
        "/auth/2fa/verify",
        json={
            "temp_token": login_data["temp_token"],
            "code": pyotp.TOTP(secret).now(),
            "user_id": login_data["user_id"],
        },
    )

    assert resp.status_code == 200
    assert "access_token" in resp.cookies


def test_2fa_verify_with_backup_code(client, use_jwt, db, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    secret = client.post("/auth/2fa/setup").json()["secret"]
    confirm_data = client.post(
        "/auth/2fa/confirm",
        json={"secret_token": pyotp.TOTP(secret).now()},
    ).json()
    backup_code = confirm_data["backup_codes"][0]

    client.cookies.clear()
    login_data = client.post(
        "/auth/login",
        data={"username": "john", "password": "secret123"},
    ).json()

    resp = client.post(
        "/auth/2fa/verify",
        json={
            "temp_token": login_data["temp_token"],
            "code": backup_code,
            "user_id": login_data["user_id"],
        },
    )

    assert resp.status_code == 200
    assert "access_token" in resp.cookies
    db.expire_all()
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    assert hash_token(backup_code) not in user.backup_codes
    assert len(user.backup_codes) == 9


def test_2fa_verify_invalid_temp_token(client, use_jwt, db, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    secret = client.post("/auth/2fa/setup").json()["secret"]
    client.post(
        "/auth/2fa/confirm",
        json={"secret_token": pyotp.TOTP(secret).now()},
    )

    client.cookies.clear()
    login_data = client.post(
        "/auth/login",
        data={"username": "john", "password": "secret123"},
    ).json()

    resp = client.post(
        "/auth/2fa/verify",
        json={
            "temp_token": "wrong-token",
            "code": pyotp.TOTP(secret).now(),
            "user_id": login_data["user_id"],
        },
    )

    assert resp.status_code == 401


def test_2fa_verify_invalid_code(client, use_jwt, db, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    secret = client.post("/auth/2fa/setup").json()["secret"]
    client.post(
        "/auth/2fa/confirm",
        json={"secret_token": pyotp.TOTP(secret).now()},
    )

    client.cookies.clear()
    login_data = client.post(
        "/auth/login",
        data={"username": "john", "password": "secret123"},
    ).json()

    resp = client.post(
        "/auth/2fa/verify",
        json={
            "temp_token": login_data["temp_token"],
            "code": "000000",
            "user_id": login_data["user_id"],
        },
    )

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /2fa/verify — rate limiting
# ---------------------------------------------------------------------------
def test_2fa_verify_rate_limits_after_max_attempts(
    client, use_jwt, db, monkeypatch, redis_client
):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    secret = client.post("/auth/2fa/setup").json()["secret"]
    client.post(
        "/auth/2fa/confirm",
        json={"secret_token": pyotp.TOTP(secret).now()},
    )

    client.cookies.clear()
    login_data = client.post(
        "/auth/login",
        data={"username": "john", "password": "secret123"},
    ).json()

    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        resp = client.post(
            "/auth/2fa/verify",
            json={
                "temp_token": login_data["temp_token"],
                "code": "000000",
                "user_id": login_data["user_id"],
            },
        )
        assert resp.status_code == 401

    resp = client.post(
        "/auth/2fa/verify",
        json={
            "temp_token": login_data["temp_token"],
            "code": "000000",
            "user_id": login_data["user_id"],
        },
    )

    assert resp.status_code == 429


def test_2fa_verify_rate_limit_blocks_valid_code(
    client, use_jwt, db, monkeypatch, redis_client
):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    secret = client.post("/auth/2fa/setup").json()["secret"]
    client.post(
        "/auth/2fa/confirm",
        json={"secret_token": pyotp.TOTP(secret).now()},
    )

    client.cookies.clear()
    login_data = client.post(
        "/auth/login",
        data={"username": "john", "password": "secret123"},
    ).json()
    user_id = login_data["user_id"]

    redis_client.set(f"2faAttempts:{user_id}", RATE_LIMIT_MAX_REQUESTS)

    resp = client.post(
        "/auth/2fa/verify",
        json={
            "temp_token": login_data["temp_token"],
            "code": pyotp.TOTP(secret).now(),
            "user_id": user_id,
        },
    )

    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# /2fa/disable
# ---------------------------------------------------------------------------
def _enable_2fa(client, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    secret = client.post("/auth/2fa/setup").json()["secret"]
    client.post(
        "/auth/2fa/confirm",
        json={"secret_token": pyotp.TOTP(secret).now()},
    )
    return secret


def test_2fa_disable_with_valid_code(client, use_jwt, db, monkeypatch):
    secret = _enable_2fa(client, monkeypatch)

    resp = client.post(
        "/auth/2fa/disable",
        json={"secret_token": pyotp.TOTP(secret).now()},
    )

    assert resp.status_code == 200
    db.expire_all()
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    assert user.totp_enabled is False
    assert user.totp_secret is None
    assert user.backup_codes is None


def test_2fa_disable_invalid_code(client, use_jwt, db, monkeypatch):
    _enable_2fa(client, monkeypatch)

    resp = client.post(
        "/auth/2fa/disable",
        json={"secret_token": "000000"},
    )

    assert resp.status_code == 401
    db.expire_all()
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    assert user.totp_enabled is True


def test_2fa_disable_when_not_enabled(client, use_jwt, db, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)

    resp = client.post(
        "/auth/2fa/disable",
        json={"secret_token": "000000"},
    )

    assert resp.status_code == 400


def test_login_no_longer_requires_2fa_after_disable(client, use_jwt, db, monkeypatch):
    secret = _enable_2fa(client, monkeypatch)
    client.post(
        "/auth/2fa/disable",
        json={"secret_token": pyotp.TOTP(secret).now()},
    )

    client.cookies.clear()
    resp = client.post(
        "/auth/login",
        data={"username": "john", "password": "secret123"},
    )

    assert resp.status_code == 200
    assert "access_token" in resp.cookies
    assert "requires_2fa" not in resp.json()


# ---------------------------------------------------------------------------
# /2fa/verify — session backend
# ---------------------------------------------------------------------------
def test_2fa_full_flow_session_backend(client, use_session, db, monkeypatch):
    enable_totp(monkeypatch)
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    secret = client.post("/auth/2fa/setup").json()["secret"]
    client.post(
        "/auth/2fa/confirm",
        json={"secret_token": pyotp.TOTP(secret).now()},
    )

    client.cookies.clear()
    login_data = client.post(
        "/auth/login",
        data={"username": "john", "password": "secret123"},
    ).json()

    resp = client.post(
        "/auth/2fa/verify",
        json={
            "temp_token": login_data["temp_token"],
            "code": pyotp.TOTP(secret).now(),
            "user_id": login_data["user_id"],
        },
    )

    assert resp.status_code == 200
    assert "session_id" in resp.cookies
