from datetime import timedelta

from app.utils import create_access_token


def _auth_headers(data):
    return {"Authorization": f"Bearer {data['access_token']}"}


def _get_referral_code(client, headers):
    response = client.get("/api/users/me/referrals", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["referral_code"]


def test_register_with_referral_code_links_referrer(client, register_user):
    referrer = register_user(email="referrer@example.com")
    code = _get_referral_code(client, _auth_headers(referrer))

    response = client.post(
        "/api/auth/register",
        json={
            "email": "referred@example.com",
            "password": "senha12345",
            "full_name": "Referred User",
            "referral_code": code,
        },
    )
    assert response.status_code == 201

    referrals = client.get("/api/users/me/referrals", headers=_auth_headers(referrer))
    data = referrals.json()
    assert data["referred_count"] == 1
    assert data["activated_count"] == 0
    assert data["referred"][0]["full_name"] == "Referred User"
    assert data["referred"][0]["is_verified"] is False


def test_register_with_invalid_referral_code_ignored(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "noref@example.com",
            "password": "senha12345",
            "full_name": "No Ref",
            "referral_code": "doesnotexist",
        },
    )
    assert response.status_code == 201


def test_verify_email_grants_bonus_slot_to_referrer_once(client, register_user):
    referrer = register_user(email="referrer2@example.com")
    code = _get_referral_code(client, _auth_headers(referrer))

    client.post(
        "/api/auth/register",
        json={
            "email": "referred2@example.com",
            "password": "senha12345",
            "full_name": "Referred Two",
            "referral_code": code,
        },
    )

    token = create_access_token(
        data={"sub": "referred2@example.com", "type": "email_verification"},
        expires_delta=timedelta(hours=24),
    )
    verify_response = client.get("/api/auth/verify-email", params={"token": token})
    assert verify_response.status_code == 200

    referrals = client.get("/api/users/me/referrals", headers=_auth_headers(referrer))
    data = referrals.json()
    assert data["bonus_app_slots"] == 1
    assert data["activated_count"] == 1

    # verificar de novo (token ainda válido) não deve conceder o bônus duas vezes
    second_verify = client.get("/api/auth/verify-email", params={"token": token})
    assert second_verify.status_code == 200

    referrals_again = client.get("/api/users/me/referrals", headers=_auth_headers(referrer))
    assert referrals_again.json()["bonus_app_slots"] == 1


def test_bonus_app_slot_allows_second_app_on_free_plan(client, register_user):
    referrer = register_user(email="referrer3@example.com")
    headers = _auth_headers(referrer)
    code = _get_referral_code(client, headers)

    client.post(
        "/api/auth/register",
        json={
            "email": "referred3@example.com",
            "password": "senha12345",
            "full_name": "Referred Three",
            "referral_code": code,
        },
    )
    token = create_access_token(
        data={"sub": "referred3@example.com", "type": "email_verification"},
        expires_delta=timedelta(hours=24),
    )
    client.get("/api/auth/verify-email", params={"token": token})

    first_app = client.post(
        "/api/apps/",
        json={"name": "App 1", "description": "", "template_type": "other"},
        headers=headers,
    )
    assert first_app.status_code == 201

    # plano free só permite 1 app, mas o bônus de indicação libera mais um
    second_app = client.post(
        "/api/apps/",
        json={"name": "App 2", "description": "", "template_type": "other"},
        headers=headers,
    )
    assert second_app.status_code == 201

    third_app = client.post(
        "/api/apps/",
        json={"name": "App 3", "description": "", "template_type": "other"},
        headers=headers,
    )
    assert third_app.status_code == 403
