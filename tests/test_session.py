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


def test_login_success(session_client):
    response = session_client.post(
        "/auth/login", data={"username": "john", "password": "secret123"}
    )
    print(response.cookies.get("session_id"))
    assert response.status_code == 200
    assert "session_id" in response.cookies


def test_test(session_client):
    response = session_client.get("/users/me")
    assert response.status_code == 200
