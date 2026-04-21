def test_register_success(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "john",
            "name": "bob",
            "password": "secret123",
            "email": "john@example.com",
        },
    )
    assert response.status_code == 200


def test_login_success(client):
    client.post(
        "/auth/register",
        json={
            "username": "john",
            "name": "bob",
            "password": "secret123",
            "email": "john@example.com",
        },
    )

    response = client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_get_me(auth_client):
    response = auth_client.get("/users/me")
    assert response.status_code == 200


def test_update_password_success(auth_client):
    response = auth_client.patch(
        "/auth/password",
        json={
            "old_password": "secret123",
            "new_password": "newpass456",
        },
    )
    assert response.status_code == 200

    login = auth_client.post(
        "/auth/login", data={"username": "john", "password": "newpass456"}
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_update_password_wrong_old_password(auth_client):
    response = auth_client.patch(
        "/auth/password",
        json={
            "old_password": "wrongpassword",
            "new_password": "newpass456",
        },
    )
    assert response.status_code == 400


def test_update_password_not_authenticated(client):
    response = client.patch(
        "/auth/password",
        json={
            "old_password": "testpass123",
            "new_password": "newpass456",
        },
    )
    assert response.status_code == 401
