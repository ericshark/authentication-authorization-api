REGISTER_PAYLOAD = {
    "username": "john",
    "name": "John Doe",
    "password": "secret123",
    "email": "john@example.com",
}


def test_register_success(client, use_session):
    response = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 200
    assert "session_id" in response.cookies


def test_register_duplicate_fails(client, use_session):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    response = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 400


def test_login_success(session_client):
    response = session_client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )
    assert response.status_code == 200
    assert "session_id" in response.cookies


def test_login_wrong_password(client, use_session):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/auth/login", data={"username": "john", "password": "wrongpass"}
    )
    assert response.status_code == 400


def test_login_wrong_username(client, use_session):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/auth/login", data={"username": "nobody", "password": "secret123"}
    )
    assert response.status_code == 400


def test_get_me(session_client):
    response = session_client.get("/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "john"
    assert data["email"] == "john@example.com"


def test_unauthenticated_request(client, use_session):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_logout(session_client):
    response = session_client.get("/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "logged out"}
    # Cookie should be cleared — subsequent request is unauthenticated
    response = session_client.get("/users/me")
    assert response.status_code == 401


def test_update_password_success(session_client):
    response = session_client.patch(
        "/auth/password",
        json={"old_password": "secret123", "new_password": "newpass456"},
    )
    assert response.status_code == 200
    # New password works at login
    login = session_client.post(
        "/auth/login", data={"username": "john", "password": "newpass456"}
    )
    assert login.status_code == 200


def test_update_password_wrong_old_password(session_client):
    response = session_client.patch(
        "/auth/password",
        json={"old_password": "wrongpassword", "new_password": "newpass456"},
    )
    assert response.status_code == 400
