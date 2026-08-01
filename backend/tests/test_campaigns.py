from app.models import BackgroundJob, Campaign, PushSendLog, User


def _published_app(client, register_user, email="campaigns@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Campanhas", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def _end_user(client, app_id, email):
    register_end_user = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": email, "password": "senha12345", "full_name": "Cliente"},
    )
    assert register_end_user.status_code == 201
    return register_end_user.json()["access_token"]


def test_create_campaign_rejects_invalid_channel(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "campaignchannel@example.com")

    response = client.post(
        f"/api/apps/{app_id}/campaigns",
        json={"channel": "sms", "segment": "all", "title": "Oi", "body": "Oi"},
        headers=owner_headers,
    )
    assert response.status_code == 400


def test_create_campaign_rejects_invalid_segment(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "campaignsegment@example.com")

    response = client.post(
        f"/api/apps/{app_id}/campaigns",
        json={"channel": "email", "segment": "vips", "title": "Oi", "body": "Oi"},
        headers=owner_headers,
    )
    assert response.status_code == 400


def test_create_campaign_rejects_blank_title_or_body(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "campaignblank@example.com")

    response = client.post(
        f"/api/apps/{app_id}/campaigns",
        json={"channel": "email", "segment": "all", "title": "  ", "body": "Oi"},
        headers=owner_headers,
    )
    assert response.status_code == 400


def test_create_campaign_requires_access(client, register_user):
    app_id, _ = _published_app(client, register_user, "campaignaccess@example.com")
    stranger = register_user(email="campaignstranger@example.com")
    stranger_headers = {"Authorization": f"Bearer {stranger['access_token']}"}

    response = client.post(
        f"/api/apps/{app_id}/campaigns",
        json={"channel": "email", "segment": "all", "title": "Oi", "body": "Oi"},
        headers=stranger_headers,
    )
    assert response.status_code == 404


def test_create_campaign_push_without_vapid_configured(client, register_user, monkeypatch):
    # O .env de dev tem uma chave VAPID real configurada (usada pelos testes
    # de push de verdade) -- aqui força vazio pra simular instância sem push.
    monkeypatch.setattr("app.routes.campaigns.settings.vapid_private_key", "")

    app_id, owner_headers = _published_app(client, register_user, "campaignnovapid@example.com")

    response = client.post(
        f"/api/apps/{app_id}/campaigns",
        json={"channel": "push", "segment": "all", "title": "Oi", "body": "Oi"},
        headers=owner_headers,
    )
    assert response.status_code == 400
    assert "não configuradas" in response.json()["detail"]


def test_create_campaign_email_segment_all_targets_every_end_user(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "campaignall@example.com")
    _end_user(client, app_id, "clientea@example.com")
    _end_user(client, app_id, "clienteb@example.com")

    response = client.post(
        f"/api/apps/{app_id}/campaigns",
        json={"channel": "email", "segment": "all", "title": "Promo", "body": "50% off"},
        headers=owner_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["recipient_count"] == 2
    assert body["channel"] == "email"
    assert body["segment"] == "all"

    jobs = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "email").all()
    recipients = {j.payload["to"] for j in jobs}
    assert {"clientea@example.com", "clienteb@example.com"} <= recipients

    campaign = db_session.query(Campaign).filter(Campaign.app_id == app_id).first()
    assert campaign is not None
    assert campaign.recipient_count == 2


def test_create_campaign_email_segment_customers_only_targets_buyers(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "campaignbuyers@example.com")
    buyer_token = _end_user(client, app_id, "comprador@example.com")
    _end_user(client, app_id, "naocomprador@example.com")

    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Bolo", "price": 20.0},
        headers=owner_headers,
    )
    item_id = item.json()["id"]
    checkout = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Comprador"}},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    order_id = checkout.json()["id"]
    client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": "completed"}, headers=owner_headers)

    response = client.post(
        f"/api/apps/{app_id}/campaigns",
        json={"channel": "email", "segment": "customers", "title": "Obrigado!", "body": "Volte sempre"},
        headers=owner_headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["recipient_count"] == 1

    jobs = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "email").all()
    recipients = {j.payload["to"] for j in jobs}
    assert "comprador@example.com" in recipients
    assert "naocomprador@example.com" not in recipients


def test_create_campaign_email_segment_non_customers_excludes_buyers(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "campaignnonbuyers@example.com")
    buyer_token = _end_user(client, app_id, "comprador2@example.com")
    _end_user(client, app_id, "naocomprador2@example.com")

    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Bolo", "price": 20.0},
        headers=owner_headers,
    )
    item_id = item.json()["id"]
    checkout = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Comprador"}},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    order_id = checkout.json()["id"]
    client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": "completed"}, headers=owner_headers)

    # A mudança de status acima já dispara uma notificação transacional por
    # e-mail pro comprador (Fase 4) -- isola só os jobs criados pela campanha,
    # já que ambos usam o mesmo job_type "email".
    jobs_before = {j.id for j in db_session.query(BackgroundJob).all()}

    response = client.post(
        f"/api/apps/{app_id}/campaigns",
        json={"channel": "email", "segment": "non_customers", "title": "Vem!", "body": "Sua primeira compra"},
        headers=owner_headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["recipient_count"] == 1

    new_jobs = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "email", ~BackgroundJob.id.in_(jobs_before)).all() if jobs_before else db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "email").all()
    recipients = {j.payload["to"] for j in new_jobs}
    assert recipients == {"naocomprador2@example.com"}


def test_create_campaign_push_sends_to_segment_and_logs(client, register_user, db_session, monkeypatch):
    monkeypatch.setattr("app.routes.push.settings.vapid_private_key", "fake-private-key")
    monkeypatch.setattr("app.routes.campaigns.settings.vapid_private_key", "fake-private-key")

    sent_calls = []
    monkeypatch.setattr("app.routes.push.webpush", lambda **kwargs: sent_calls.append(kwargs))

    app_id, owner_headers = _published_app(client, register_user, "campaignpush@example.com")
    # push_sends_per_month é 0 no plano free -- sobe pra "pro" só pra testar o
    # envio em si, não o limite (mesmo padrão de test_push.py).
    owner = db_session.query(User).filter(User.email == "campaignpush@example.com").first()
    owner.plan = "pro"
    db_session.commit()
    buyer_token = _end_user(client, app_id, "compradorpush@example.com")
    non_buyer_token = _end_user(client, app_id, "naocompradorpush@example.com")

    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Bolo", "price": 20.0},
        headers=owner_headers,
    )
    item_id = item.json()["id"]
    checkout = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Comprador"}},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    order_id = checkout.json()["id"]
    client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": "completed"}, headers=owner_headers)

    client.post(
        f"/api/apps/{app_id}/public/push/subscribe",
        json={"endpoint": "https://fcm.example.com/buyer", "keys": {"p256dh": "x", "auth": "y"}},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    client.post(
        f"/api/apps/{app_id}/public/push/subscribe",
        json={"endpoint": "https://fcm.example.com/nonbuyer", "keys": {"p256dh": "x", "auth": "y"}},
        headers={"Authorization": f"Bearer {non_buyer_token}"},
    )

    response = client.post(
        f"/api/apps/{app_id}/campaigns",
        json={"channel": "push", "segment": "customers", "title": "Obrigado!", "body": "Volte sempre"},
        headers=owner_headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["recipient_count"] == 1
    assert len(sent_calls) == 1

    log = db_session.query(PushSendLog).filter(PushSendLog.app_id == app_id).first()
    assert log is not None
    assert log.title == "Obrigado!"


def test_list_campaigns_requires_access(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "campaignlist@example.com")
    stranger = register_user(email="campaignliststranger@example.com")
    stranger_headers = {"Authorization": f"Bearer {stranger['access_token']}"}

    client.post(
        f"/api/apps/{app_id}/campaigns",
        json={"channel": "email", "segment": "all", "title": "Oi", "body": "Oi"},
        headers=owner_headers,
    )

    denied = client.get(f"/api/apps/{app_id}/campaigns", headers=stranger_headers)
    assert denied.status_code == 404

    listed = client.get(f"/api/apps/{app_id}/campaigns", headers=owner_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
