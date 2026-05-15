def test_get_me(jwt_client):
    response = jwt_client.get("/users/me")
    assert response.status_code == 200


def test_update_password_success(jwt_client):
    response = jwt_client.patch(
        "/auth/password",
        json={
            "old_password": "secret123",
            "new_password": "newpass456",
        },
    )
    assert response.status_code == 200

    response = jwt_client.post(
        "/auth/login", data={"username": "john", "password": "newpass456"}
    )
    assert response.status_code == 200
    assert "access_token" in response.cookies


def test_update_password_wrong_old_password(jwt_client):
    response = jwt_client.patch(
        "/auth/password",
        json={
            "old_password": "wrongpassword",
            "new_password": "newpass456",
        },
    )
    assert response.status_code == 400
