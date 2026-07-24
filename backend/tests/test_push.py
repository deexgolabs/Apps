from app.models import PushSubscription


def _published_app(client, register_user, email="push@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Push", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def test_subscribe_stores_subscription(client, register_user, db_session):
    app_id, _ = _published_app(client, register_user)

    response = client.post(
        f"/api/apps/{app_id}/public/push/subscribe",
        json={
            "endpoint": "https://fcm.example.com/send/abc123",
            "keys": {"p256dh": "fake-p256dh", "auth": "fake-auth"},
        },
    )
    assert response.status_code == 201

    subscription = db_session.query(PushSubscription).filter(PushSubscription.app_id == app_id).first()
    assert subscription is not None
    assert subscription.endpoint == "https://fcm.example.com/send/abc123"


def test_subscribe_fails_for_draft_app(client, register_user):
    data = register_user(email="pushdraft@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Draft", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]

    response = client.post(
        f"/api/apps/{app_id}/public/push/subscribe",
        json={"endpoint": "https://fcm.example.com/send/xyz", "keys": {"p256dh": "a", "auth": "b"}},
    )
    assert response.status_code == 404


def test_send_requires_owner_authentication(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "pushowner@example.com")
    other = register_user(email="pushother@example.com")
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    response = client.post(
        f"/api/apps/{app_id}/push/send",
        json={"title": "Oi", "body": "Teste"},
        headers=other_headers,
    )
    assert response.status_code == 404

    unauthenticated = client.post(f"/api/apps/{app_id}/push/send", json={"title": "Oi", "body": "Teste"})
    assert unauthenticated.status_code == 401

    owner_response = client.post(
        f"/api/apps/{app_id}/push/send",
        json={"title": "Oi", "body": "Teste"},
        headers=owner_headers,
    )
    # dono autenticado e VAPID configurado: envia para 0 inscritos (nenhum se inscreveu neste app)
    assert owner_response.status_code == 200
    assert owner_response.json() == {"sent": 0, "failed": 0, "total": 0}
