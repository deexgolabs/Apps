from datetime import timedelta

from app.utils import create_access_token


def test_register_returns_token(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "senha12345", "full_name": "New User"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["access_token"]
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["is_verified"] is False
    assert data["user"]["is_admin"] is False


def test_register_duplicate_email_fails(client, register_user):
    register_user(email="dup@example.com")
    response = client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "outrasenha", "full_name": "Outro"},
    )
    assert response.status_code == 400


def test_login_wrong_password_fails(client, register_user):
    register_user(email="login@example.com", password="senhacerta")
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "senhaerrada"},
    )
    assert response.status_code == 401


def test_login_correct_password_succeeds(client, register_user):
    register_user(email="login2@example.com", password="senhacerta")
    response = client.post(
        "/api/auth/login",
        json={"email": "login2@example.com", "password": "senhacerta"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_forgot_password_always_returns_generic_message(client, register_user):
    register_user(email="reset@example.com")
    response = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"})
    assert response.status_code == 200

    response_unknown = client.post("/api/auth/forgot-password", json={"email": "naoexiste@example.com"})
    assert response_unknown.status_code == 200
    assert response_unknown.json() == response.json()


def test_reset_password_happy_path(client, register_user):
    register_user(email="reset2@example.com", password="senhaantiga")

    token = create_access_token(
        data={"sub": "reset2@example.com", "type": "password_reset"},
        expires_delta=timedelta(hours=1),
    )
    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "senhanova123"},
    )
    assert response.status_code == 200

    login = client.post(
        "/api/auth/login",
        json={"email": "reset2@example.com", "password": "senhanova123"},
    )
    assert login.status_code == 200


def test_reset_password_rejects_wrong_token_type(client, register_user):
    register_user(email="reset3@example.com")
    token = create_access_token(
        data={"sub": "reset3@example.com", "type": "email_verification"},
        expires_delta=timedelta(hours=1),
    )
    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "outrasenha"},
    )
    assert response.status_code == 400


def test_verify_email_happy_path(client, register_user):
    register_user(email="verify@example.com")
    token = create_access_token(
        data={"sub": "verify@example.com", "type": "email_verification"},
        expires_delta=timedelta(hours=24),
    )
    response = client.get("/api/auth/verify-email", params={"token": token})
    assert response.status_code == 200
