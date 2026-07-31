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


def test_confirm_sets_plan_expiration_30_days_out(client, register_user):
    from datetime import datetime, timezone

    data = register_user(email="billing4@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    response = client.post("/api/billing/confirm", json={"plan": "pro"}, headers=headers)
    assert response.status_code == 200
    expires_at = datetime.fromisoformat(response.json()["plan_expires_at"])
    days_out = (expires_at - datetime.now(timezone.utc)).days
    assert 28 <= days_out <= 30


def test_expired_plan_auto_downgrades_to_free(client, register_user, db_session):
    from datetime import timedelta
    from app.models import User, utcnow

    data = register_user(email="billing5@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    user = db_session.query(User).filter(User.email == "billing5@example.com").first()
    user.plan = "pro"
    user.plan_expires_at = utcnow() - timedelta(days=1)
    db_session.commit()

    me = client.get("/api/users/me", headers=headers)
    assert me.json()["plan"] == "free"
    assert me.json()["plan_expires_at"] is None


def test_active_plan_not_downgraded_before_expiration(client, register_user, db_session):
    from datetime import timedelta
    from app.models import User, utcnow

    data = register_user(email="billing6@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    user = db_session.query(User).filter(User.email == "billing6@example.com").first()
    user.plan = "pro"
    user.plan_expires_at = utcnow() + timedelta(days=15)
    db_session.commit()

    me = client.get("/api/users/me", headers=headers)
    assert me.json()["plan"] == "pro"
