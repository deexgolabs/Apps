from app.models import PushSubscription, User


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


def test_send_requires_owner_authentication(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "pushowner@example.com")
    # push_sends_per_month é 0 no plano free (não vende push pra esse plano) —
    # sobe pra "pro" só pra testar a autenticação/autorização, não o limite.
    owner = db_session.query(User).filter(User.email == "pushowner@example.com").first()
    owner.plan = "pro"
    db_session.commit()
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


def test_send_blocked_for_free_plan(client, register_user):
    """Plano free tem push_sends_per_month = 0 — nem o dono consegue enviar."""
    app_id, owner_headers = _published_app(client, register_user, "pushfree@example.com")

    response = client.post(
        f"/api/apps/{app_id}/push/send",
        json={"title": "Oi", "body": "Teste"},
        headers=owner_headers,
    )
    assert response.status_code == 403
    assert "upgrade" in response.json()["detail"].lower()


def test_push_history_records_title_and_body(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "pushhistory@example.com")
    owner = db_session.query(User).filter(User.email == "pushhistory@example.com").first()
    owner.plan = "pro"
    db_session.commit()

    send = client.post(
        f"/api/apps/{app_id}/push/send",
        json={"title": "Promoção", "body": "50% off hoje"},
        headers=owner_headers,
    )
    assert send.status_code == 200

    history = client.get(f"/api/apps/{app_id}/push/history", headers=owner_headers)
    assert history.status_code == 200
    entries = history.json()
    assert len(entries) == 1
    assert entries[0]["title"] == "Promoção"
    assert entries[0]["body"] == "50% off hoje"


def test_send_respects_monthly_limit(client, register_user, db_session):
    """Plano pro tem push_sends_per_month = 5 — o 6º envio no mês deve ser bloqueado."""
    app_id, owner_headers = _published_app(client, register_user, "pushlimit@example.com")
    owner = db_session.query(User).filter(User.email == "pushlimit@example.com").first()
    owner.plan = "pro"
    db_session.commit()

    for _ in range(5):
        response = client.post(
            f"/api/apps/{app_id}/push/send",
            json={"title": "Oi", "body": "Teste"},
            headers=owner_headers,
        )
        assert response.status_code == 200

    blocked = client.post(
        f"/api/apps/{app_id}/push/send",
        json={"title": "Oi", "body": "Teste"},
        headers=owner_headers,
    )
    assert blocked.status_code == 403
    assert "upgrade" in blocked.json()["detail"].lower()
