def test_checkout_fails_when_gateway_not_configured(client, register_user):
    data = register_user(email="billing@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    response = client.post(
        "/api/billing/checkout",
        json={"gateway": "mercado_pago", "plan": "pro"},
        headers=headers,
    )
    assert response.status_code == 400


def test_checkout_rejects_invalid_plan(client, register_user):
    data = register_user(email="billing2@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    response = client.post(
        "/api/billing/checkout",
        json={"gateway": "mercado_pago", "plan": "unlimited"},
        headers=headers,
    )
    assert response.status_code == 400


def test_confirm_updates_user_plan(client, register_user):
    data = register_user(email="billing3@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    response = client.post("/api/billing/confirm", json={"plan": "pro"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["plan"] == "pro"

    me = client.get("/api/users/me", headers=headers)
    assert me.json()["plan"] == "pro"
