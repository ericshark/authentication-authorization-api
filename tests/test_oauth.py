from fastapi import HTTPException
from starlette.responses import RedirectResponse
from sqlalchemy import select

from app.models import SocialAccount, User


class FakeGitHubResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def test_google_sign_in_redirects_to_provider(client, monkeypatch):
    async def fake_authorize_redirect(request, redirect_uri):
        assert redirect_uri
        return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth")

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.google.authorize_redirect",
        fake_authorize_redirect,
    )

    response = client.get("/auth/google", follow_redirects=False)

    assert response.status_code in {302, 307}
    assert response.headers["location"] == "https://accounts.google.com/o/oauth2/v2/auth"


def test_google_callback_creates_user_and_social_account(client, use_jwt, db, monkeypatch):
    async def fake_authorize_access_token(request):
        return {"userinfo": {"sub": "google-123", "email": "google@example.com"}}

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.google.authorize_access_token",
        fake_authorize_access_token,
    )

    response = client.get("/auth/google/callback")

    assert response.status_code == 200
    assert "access_token" in response.cookies

    user = db.execute(select(User).where(User.email == "google@example.com")).scalar_one()
    social = db.execute(
        select(SocialAccount).where(
            SocialAccount.provider == "google",
            SocialAccount.provider_id == "google-123",
        )
    ).scalar_one()
    assert social.user_id == user.id


def test_google_callback_links_existing_user_by_email(client, use_jwt, db, monkeypatch):
    client.post(
        "/auth/register",
        json={
            "username": "googleuser",
            "name": "Google User",
            "password": "secret123",
            "email": "google@example.com",
        },
    )
    existing_user = db.execute(
        select(User).where(User.email == "google@example.com")
    ).scalar_one()
    client.cookies.clear()

    async def fake_authorize_access_token(request):
        return {"userinfo": {"sub": "google-123", "email": "google@example.com"}}

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.google.authorize_access_token",
        fake_authorize_access_token,
    )

    response = client.get("/auth/google/callback")

    assert response.status_code == 200
    social = db.execute(select(SocialAccount)).scalar_one()
    assert social.user_id == existing_user.id


def test_google_callback_reuses_existing_social_account(client, use_jwt, db, monkeypatch):
    async def fake_authorize_access_token(request):
        return {"userinfo": {"sub": "google-123", "email": "google@example.com"}}

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.google.authorize_access_token",
        fake_authorize_access_token,
    )

    client.get("/auth/google/callback")
    client.cookies.clear()
    response = client.get("/auth/google/callback")

    assert response.status_code == 200
    assert len(db.execute(select(SocialAccount)).scalars().all()) == 1


def test_google_callback_rejects_missing_user_info(client, use_jwt, monkeypatch):
    async def fake_authorize_access_token(request):
        return {"userinfo": {"sub": "google-123"}}

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.google.authorize_access_token",
        fake_authorize_access_token,
    )

    response = client.get("/auth/google/callback")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Google user info"


def test_github_sign_in_redirects_to_provider(client, monkeypatch):
    async def fake_authorize_redirect(request, redirect_uri):
        assert redirect_uri
        return RedirectResponse("https://github.com/login/oauth/authorize")

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.github.authorize_redirect",
        fake_authorize_redirect,
    )

    response = client.get("/auth/github", follow_redirects=False)

    assert response.status_code in {302, 307}
    assert response.headers["location"] == "https://github.com/login/oauth/authorize"


def test_github_callback_creates_user_and_social_account(client, use_jwt, db, monkeypatch):
    async def fake_authorize_access_token(request):
        return {"access_token": "token"}

    async def fake_get(url, token):
        return FakeGitHubResponse({"id": 456, "email": "github@example.com"})

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.github.authorize_access_token",
        fake_authorize_access_token,
    )
    monkeypatch.setattr("app.routes.oauth_routes.oauth.github.get", fake_get)

    response = client.get("/auth/github/callback")

    assert response.status_code == 200
    assert "access_token" in response.cookies

    user = db.execute(select(User).where(User.email == "github@example.com")).scalar_one()
    social = db.execute(
        select(SocialAccount).where(
            SocialAccount.provider == "github",
            SocialAccount.provider_id == "456",
        )
    ).scalar_one()
    assert social.user_id == user.id


def test_github_callback_links_existing_user_by_email(client, use_jwt, db, monkeypatch):
    client.post(
        "/auth/register",
        json={
            "username": "githubuser",
            "name": "GitHub User",
            "password": "secret123",
            "email": "github@example.com",
        },
    )
    existing_user = db.execute(
        select(User).where(User.email == "github@example.com")
    ).scalar_one()
    client.cookies.clear()

    async def fake_authorize_access_token(request):
        return {"access_token": "token"}

    async def fake_get(url, token):
        return FakeGitHubResponse({"id": 456, "email": "github@example.com"})

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.github.authorize_access_token",
        fake_authorize_access_token,
    )
    monkeypatch.setattr("app.routes.oauth_routes.oauth.github.get", fake_get)

    response = client.get("/auth/github/callback")

    assert response.status_code == 200
    social = db.execute(select(SocialAccount)).scalar_one()
    assert social.user_id == existing_user.id


def test_github_callback_reuses_existing_social_account(client, use_jwt, db, monkeypatch):
    async def fake_authorize_access_token(request):
        return {"access_token": "token"}

    async def fake_get(url, token):
        return FakeGitHubResponse({"id": 456, "email": "github@example.com"})

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.github.authorize_access_token",
        fake_authorize_access_token,
    )
    monkeypatch.setattr("app.routes.oauth_routes.oauth.github.get", fake_get)

    client.get("/auth/github/callback")
    client.cookies.clear()
    response = client.get("/auth/github/callback")

    assert response.status_code == 200
    assert len(db.execute(select(SocialAccount)).scalars().all()) == 1


def test_github_callback_rejects_private_email(client, use_jwt, monkeypatch):
    async def fake_authorize_access_token(request):
        return {"access_token": "token"}

    async def fake_get(url, token):
        return FakeGitHubResponse({"id": 456, "email": None})

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.github.authorize_access_token",
        fake_authorize_access_token,
    )
    monkeypatch.setattr("app.routes.oauth_routes.oauth.github.get", fake_get)

    response = client.get("/auth/github/callback")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Please make your GitHub email public to use this login method"
    )


def test_github_callback_maps_oauth_error_to_400(client, use_jwt, monkeypatch):
    async def fake_authorize_access_token(request):
        raise HTTPException(status_code=400, detail="OAuth authentication failed")

    monkeypatch.setattr(
        "app.routes.oauth_routes.oauth.github.authorize_access_token",
        fake_authorize_access_token,
    )

    response = client.get("/auth/github/callback")

    assert response.status_code == 400
