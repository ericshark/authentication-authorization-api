from sqlalchemy import select

from app.models import RoleEnum, SocialAccount, User


def make_admin(db):
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    user.role = RoleEnum.ADMIN
    db.commit()
    return user


def test_root_returns_status(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_route_is_registered(client):
    response = client.get("/auth/health")

    assert response.status_code == 200
    assert response.json() is None


def test_google_sign_in_route_is_registered(client):
    response = client.get("/auth/google", follow_redirects=False)

    assert response.status_code in {302, 307}


def test_google_callback_creates_social_account(client, use_jwt, db, monkeypatch):
    async def fake_authorize_access_token(request):
        return {"userinfo": {"sub": "google-123", "email": "oauth@example.com"}}

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.google.authorize_access_token",
        fake_authorize_access_token,
    )

    response = client.get("/auth/google/callback")

    assert response.status_code == 200
    assert "access_token" in response.cookies

    user = db.execute(select(User).where(User.email == "oauth@example.com")).scalar_one()
    social = db.execute(
        select(SocialAccount).where(SocialAccount.provider_id == "google-123")
    ).scalar_one()
    assert social.provider == "google"
    assert social.user_id == user.id


def test_google_callback_uses_existing_social_account(
    client, use_jwt, db, monkeypatch
):
    async def fake_authorize_access_token(request):
        return {"userinfo": {"sub": "google-123", "email": "oauth@example.com"}}

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.google.authorize_access_token",
        fake_authorize_access_token,
    )
    client.get("/auth/google/callback")
    client.cookies.clear()

    response = client.get("/auth/google/callback")

    assert response.status_code == 200
    assert "access_token" in response.cookies
    social_accounts = db.execute(select(SocialAccount)).scalars().all()
    assert len(social_accounts) == 1
    assert social_accounts[0].provider_id == "google-123"


def test_update_me_updates_current_user(jwt_client, db):
    response = jwt_client.patch(
        "/users/update-me",
        json={"name": "Johnny", "email": "johnny@example.com"},
    )

    assert response.status_code == 200
    user = db.execute(select(User).where(User.username == "john")).scalar_one()
    assert response.json() == {"updated_id": user.id}
    assert user.name == "Johnny"
    assert user.email == "johnny@example.com"


def test_update_me_with_no_fields_returns_current_user_id(jwt_client, db):
    user = db.execute(select(User).where(User.username == "john")).scalar_one()

    response = jwt_client.patch("/users/update-me", json={})

    assert response.status_code == 200
    assert response.json() == {"updated_id": user.id}


def test_admin_can_list_users(jwt_client, db):
    make_admin(db)

    response = jwt_client.get("/admin/users")

    assert response.status_code == 200
    assert response.json()[0]["username"] == "john"


def test_admin_can_change_user_role(jwt_client, db):
    admin = make_admin(db)

    response = jwt_client.patch(
        f"/admin/{admin.id}/role",
        json={"role": "moderator"},
    )

    assert response.status_code == 200
    assert response.json() == {"updated_id": admin.id, "new_role": "moderator"}
    db.refresh(admin)
    assert admin.role == RoleEnum.MODERATOR


def test_admin_change_role_unknown_user_returns_404(jwt_client, db):
    make_admin(db)

    response = jwt_client.patch("/admin/999/role", json={"role": "moderator"})

    assert response.status_code == 404


def test_admin_can_unlock_user(jwt_client, db, redis_client):
    make_admin(db)
    redis_client.set("failed:jane", "5")

    response = jwt_client.post("/admin/unlock/jane")

    assert response.status_code == 200
    assert response.json() == {"message": "succesful reset for: jane"}
    assert redis_client.get("failed:jane") is None
