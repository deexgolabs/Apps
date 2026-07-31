import hashlib
import hmac
import json

from app.models import BackgroundJob


def _auth_headers(data):
    return {"Authorization": f"Bearer {data['access_token']}"}


def _published_app(client, register_user, email):
    data = register_user(email=email)
    headers = _auth_headers(data)
    create = client.post(
        "/api/apps/",
        json={"name": "App Webhook Sub", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def test_create_webhook_subscription_returns_secret(client, register_user):
    app_id, headers = _published_app(client, register_user, "wh1@example.com")

    response = client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "https://example.com/hook", "event": "order.created"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["url"] == "https://example.com/hook"
    assert body["event"] == "order.created"
    assert body["active"] is True
    assert len(body["secret"]) >= 32


def test_create_webhook_subscription_rejects_invalid_event(client, register_user):
    app_id, headers = _published_app(client, register_user, "wh2@example.com")

    response = client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "https://example.com/hook", "event": "order.exploded"},
        headers=headers,
    )
    assert response.status_code == 400


def test_create_webhook_subscription_rejects_invalid_url(client, register_user):
    app_id, headers = _published_app(client, register_user, "wh3@example.com")

    response = client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "not-a-url", "event": "order.created"},
        headers=headers,
    )
    assert response.status_code == 400


def test_create_webhook_subscription_enforces_max_limit(client, register_user):
    app_id, headers = _published_app(client, register_user, "wh4@example.com")

    for i in range(5):
        response = client.post(
            f"/api/apps/{app_id}/webhooks/subscriptions",
            json={"url": f"https://example.com/hook{i}", "event": "*"},
            headers=headers,
        )
        assert response.status_code == 201

    sixth = client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "https://example.com/hook6", "event": "*"},
        headers=headers,
    )
    assert sixth.status_code == 400


def test_list_webhook_subscriptions_requires_owner(client, register_user):
    app_id, headers = _published_app(client, register_user, "wh5owner@example.com")
    other = register_user(email="wh5other@example.com")
    other_headers = _auth_headers(other)

    client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "https://example.com/hook", "event": "order.created"},
        headers=headers,
    )

    response = client.get(f"/api/apps/{app_id}/webhooks/subscriptions", headers=other_headers)
    assert response.status_code == 404


def test_update_webhook_subscription_can_deactivate(client, register_user):
    app_id, headers = _published_app(client, register_user, "wh6@example.com")
    created = client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "https://example.com/hook", "event": "order.created"},
        headers=headers,
    ).json()

    response = client.put(
        f"/api/apps/{app_id}/webhooks/subscriptions/{created['id']}",
        json={"active": False},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["active"] is False


def test_delete_webhook_subscription(client, register_user):
    app_id, headers = _published_app(client, register_user, "wh7@example.com")
    created = client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "https://example.com/hook", "event": "order.created"},
        headers=headers,
    ).json()

    response = client.delete(f"/api/apps/{app_id}/webhooks/subscriptions/{created['id']}", headers=headers)
    assert response.status_code == 204

    listed = client.get(f"/api/apps/{app_id}/webhooks/subscriptions", headers=headers).json()
    assert listed == []


def test_creating_order_enqueues_signed_webhook_job(client, register_user, db_session):
    app_id, headers = _published_app(client, register_user, "wh8@example.com")
    subscription = client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "https://example.com/hook", "event": "order.created"},
        headers=headers,
    ).json()

    order = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
    )
    assert order.status_code == 201

    jobs = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "webhook").all()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.payload["url"] == "https://example.com/hook"
    assert job.payload["body"]["event"] == "order.created"
    assert job.payload["body"]["data"]["order_id"] == order.json()["id"]

    expected_signature = hmac.new(
        subscription["secret"].encode(),
        json.dumps(job.payload["body"], sort_keys=True, default=str).encode(),
        hashlib.sha256,
    ).hexdigest()
    assert job.payload["headers"]["X-Webhook-Signature"] == f"sha256={expected_signature}"


def test_order_status_change_enqueues_webhook_for_matching_event(client, register_user, db_session):
    app_id, headers = _published_app(client, register_user, "wh9@example.com")
    client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "https://example.com/status-hook", "event": "order.status_changed"},
        headers=headers,
    )

    order = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
    ).json()

    before = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "webhook").count()
    client.put(f"/api/apps/{app_id}/orders/{order['id']}", json={"status": "confirmed"}, headers=headers)
    after = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "webhook").all()

    assert len(after) == before + 1
    assert after[-1].payload["url"] == "https://example.com/status-hook"
    assert after[-1].payload["body"]["data"]["status"] == "confirmed"


def test_subscription_only_fires_for_its_own_event(client, register_user, db_session):
    app_id, headers = _published_app(client, register_user, "wh10@example.com")
    client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "https://example.com/only-created", "event": "order.created"},
        headers=headers,
    )

    order = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
    ).json()

    before = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "webhook").count()
    client.put(f"/api/apps/{app_id}/orders/{order['id']}", json={"status": "confirmed"}, headers=headers)
    after = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "webhook").count()

    assert after == before  # a assinatura só escuta order.created, não deve disparar de novo aqui


def test_wildcard_subscription_receives_all_events(client, register_user, db_session):
    app_id, headers = _published_app(client, register_user, "wh11@example.com")
    client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "https://example.com/all", "event": "*"},
        headers=headers,
    )

    order = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
    ).json()
    client.put(f"/api/apps/{app_id}/orders/{order['id']}", json={"status": "confirmed"}, headers=headers)

    jobs = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "webhook").all()
    events = [job.payload["body"]["event"] for job in jobs]
    assert "order.created" in events
    assert "order.status_changed" in events


def test_inactive_subscription_does_not_receive_events(client, register_user, db_session):
    app_id, headers = _published_app(client, register_user, "wh12@example.com")
    created = client.post(
        f"/api/apps/{app_id}/webhooks/subscriptions",
        json={"url": "https://example.com/inactive", "event": "order.created"},
        headers=headers,
    ).json()
    client.put(
        f"/api/apps/{app_id}/webhooks/subscriptions/{created['id']}",
        json={"active": False},
        headers=headers,
    )

    client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
    )

    jobs = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "webhook").all()
    assert jobs == []
