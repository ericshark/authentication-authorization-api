REGISTER_PAYLOAD = {
    "username": "john",
    "name": "John Doe",
    "password": "secret123",
    "email": "john@example.com",
}


def test_register_sets_refresh_token(client, use_jwt_with_refresh):
    response = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


def test_login_sets_refresh_token(client, use_jwt_with_refresh):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )
    assert response.status_code == 200
    assert "refresh_token" in response.cookies


def test_refresh_returns_new_access_token(jwt_refresh_client):
    response = jwt_refresh_client.get("/auth/refresh")
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert response.json() == {"message": "success new jwt"}


def test_refresh_without_token_returns_401(client, use_jwt_with_refresh):
    response = client.get("/auth/refresh")
    assert response.status_code == 401


def test_refresh_disabled_returns_404(client, use_jwt):
    response = client.get("/auth/refresh")
    assert response.status_code == 404


def test_logout_invalidates_refresh_token(jwt_refresh_client):
    old_refresh = jwt_refresh_client.cookies.get("refresh_token")
    logout = jwt_refresh_client.get("/auth/logout")
    assert logout.status_code == 200
    jwt_refresh_client.cookies.clear()
    jwt_refresh_client.cookies.update({"refresh_token": old_refresh})
    response = jwt_refresh_client.get("/auth/refresh")
    assert response.status_code == 401


def test_logout_all_invalidates_all_refresh_tokens(jwt_refresh_client):
    old_refresh = jwt_refresh_client.cookies.get("refresh_token")
    logout = jwt_refresh_client.get("/auth/logout-all")
    assert logout.status_code == 200
    jwt_refresh_client.cookies.clear()
    jwt_refresh_client.cookies.update({"refresh_token": old_refresh})
    response = jwt_refresh_client.get("/auth/refresh")
    assert response.status_code == 401


def test_update_password_invalidates_all_refresh_tokens(jwt_refresh_client):
    old_refresh = jwt_refresh_client.cookies.get("refresh_token")
    response = jwt_refresh_client.patch(
        "/auth/password",
        json={"old_password": "secret123", "new_password": "newpass456"},
    )
    assert response.status_code == 200
    jwt_refresh_client.cookies.clear()
    jwt_refresh_client.cookies.update({"refresh_token": old_refresh})
    response = jwt_refresh_client.get("/auth/refresh")
    assert response.status_code == 401
