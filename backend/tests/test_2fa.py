import pyotp


def _auth_headers(data):
    return {"Authorization": f"Bearer {data['access_token']}"}


def _setup_and_enable(client, headers):
    setup = client.post("/api/auth/2fa/setup", headers=headers)
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_url"].startswith("otpauth://totp/")

    code = pyotp.TOTP(secret).now()
    enable = client.post("/api/auth/2fa/enable", json={"code": code}, headers=headers)
    assert enable.status_code == 200, enable.text
    return secret, enable.json()["recovery_codes"]


def test_2fa_setup_returns_secret_and_otpauth_url(client, register_user):
    data = register_user(email="twofa1@example.com")
    headers = _auth_headers(data)

    response = client.post("/api/auth/2fa/setup", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["secret"]) >= 16


def test_2fa_enable_rejects_invalid_code(client, register_user):
    data = register_user(email="twofa2@example.com")
    headers = _auth_headers(data)

    client.post("/api/auth/2fa/setup", headers=headers)
    response = client.post("/api/auth/2fa/enable", json={"code": "000000"}, headers=headers)
    assert response.status_code == 400


def test_2fa_enable_with_valid_code_activates_and_returns_8_recovery_codes(client, register_user):
    data = register_user(email="twofa3@example.com")
    headers = _auth_headers(data)

    _, recovery_codes = _setup_and_enable(client, headers)
    assert len(recovery_codes) == 8
    assert len(set(recovery_codes)) == 8

    me = client.get("/api/users/me", headers=headers)
    assert me.json()["totp_enabled"] is True


def test_login_with_2fa_enabled_requires_verification(client, register_user):
    data = register_user(email="twofa4@example.com", password="senha12345")
    headers = _auth_headers(data)
    _setup_and_enable(client, headers)

    login = client.post("/api/auth/login", json={"email": "twofa4@example.com", "password": "senha12345"})
    assert login.status_code == 200
    body = login.json()
    assert body["requires_2fa"] is True
    assert body["temp_token"]
    assert "access_token" not in body


def test_2fa_verify_login_with_valid_totp_code_succeeds(client, register_user):
    data = register_user(email="twofa5@example.com", password="senha12345")
    headers = _auth_headers(data)
    secret, _ = _setup_and_enable(client, headers)

    login = client.post("/api/auth/login", json={"email": "twofa5@example.com", "password": "senha12345"})
    temp_token = login.json()["temp_token"]

    code = pyotp.TOTP(secret).now()
    verify = client.post("/api/auth/2fa/verify-login", json={"temp_token": temp_token, "code": code})
    assert verify.status_code == 200
    assert verify.json()["access_token"]
    assert verify.json()["user"]["email"] == "twofa5@example.com"


def test_2fa_verify_login_with_invalid_code_fails(client, register_user):
    data = register_user(email="twofa6@example.com", password="senha12345")
    headers = _auth_headers(data)
    _setup_and_enable(client, headers)

    login = client.post("/api/auth/login", json={"email": "twofa6@example.com", "password": "senha12345"})
    temp_token = login.json()["temp_token"]

    verify = client.post("/api/auth/2fa/verify-login", json={"temp_token": temp_token, "code": "000000"})
    assert verify.status_code == 401


def test_2fa_verify_login_with_recovery_code_works_once(client, register_user):
    data = register_user(email="twofa7@example.com", password="senha12345")
    headers = _auth_headers(data)
    _, recovery_codes = _setup_and_enable(client, headers)
    recovery_code = recovery_codes[0]

    login = client.post("/api/auth/login", json={"email": "twofa7@example.com", "password": "senha12345"})
    temp_token = login.json()["temp_token"]

    first_use = client.post("/api/auth/2fa/verify-login", json={"temp_token": temp_token, "code": recovery_code})
    assert first_use.status_code == 200

    login2 = client.post("/api/auth/login", json={"email": "twofa7@example.com", "password": "senha12345"})
    temp_token2 = login2.json()["temp_token"]
    second_use = client.post("/api/auth/2fa/verify-login", json={"temp_token": temp_token2, "code": recovery_code})
    assert second_use.status_code == 401


def test_2fa_disable_requires_correct_password(client, register_user):
    data = register_user(email="twofa8@example.com", password="senha12345")
    headers = _auth_headers(data)
    _setup_and_enable(client, headers)

    response = client.post("/api/auth/2fa/disable", json={"password": "senhaerrada"}, headers=headers)
    assert response.status_code == 401


def test_2fa_disable_clears_state_and_login_works_normally(client, register_user):
    data = register_user(email="twofa9@example.com", password="senha12345")
    headers = _auth_headers(data)
    _setup_and_enable(client, headers)

    response = client.post("/api/auth/2fa/disable", json={"password": "senha12345"}, headers=headers)
    assert response.status_code == 200

    me = client.get("/api/users/me", headers=headers)
    assert me.json()["totp_enabled"] is False

    login = client.post("/api/auth/login", json={"email": "twofa9@example.com", "password": "senha12345"})
    assert login.status_code == 200
    assert login.json()["access_token"]
