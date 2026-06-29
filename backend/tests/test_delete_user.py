from sqlalchemy import select

from app.models import RefreshToken, User


def test_delete_user_deactivates_jwt_account(jwt_client, db):
    response = jwt_client.delete("/users/me/delete")

    assert response.status_code == 200
    assert response.json() == {"message": "deleted account"}

    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    assert user.is_active is False

    get_me = jwt_client.get("/users/me")
    assert get_me.status_code == 401

    login = jwt_client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )
    assert login.status_code == 400


def test_delete_user_deactivates_session_account(session_client, db):
    response = session_client.delete("/users/me/delete")

    assert response.status_code == 200
    assert response.json() == {"message": "deleted account"}

    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    assert user.is_active is False

    get_me = session_client.get("/users/me")
    assert get_me.status_code == 401

    login = session_client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )
    assert login.status_code == 400


def test_delete_user_invalidates_refresh_tokens(jwt_refresh_client, db):
    old_refresh = jwt_refresh_client.cookies.get("refresh_token")

    response = jwt_refresh_client.delete("/users/me/delete")

    assert response.status_code == 200
    assert response.json() == {"message": "deleted account"}

    refresh_tokens = db.execute(select(RefreshToken)).scalars().all()
    assert refresh_tokens
    assert all(token.valid is False for token in refresh_tokens)

    jwt_refresh_client.cookies.clear()
    jwt_refresh_client.cookies.update({"refresh_token": old_refresh})
    refresh = jwt_refresh_client.get("/auth/refresh")
    assert refresh.status_code == 401


def test_refresh_rejects_inactive_user(jwt_refresh_client, db):
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    user.is_active = False
    db.commit()

    response = jwt_refresh_client.get("/auth/refresh")

    assert response.status_code == 401
