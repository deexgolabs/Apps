import pyotp


def _auth_headers(data):
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_create_app_logs_audit_entry(client, register_user):
    data = register_user(email="audit1@example.com")
    headers = _auth_headers(data)

    create = client.post(
        "/api/apps/",
        json={"name": "App Auditoria", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]

    logs = client.get("/api/audit-logs/", headers=headers)
    assert logs.status_code == 200
    entries = logs.json()
    assert any(e["action"] == "create_app" and e["app_id"] == app_id for e in entries)


def test_publish_app_logs_status_change(client, register_user):
    data = register_user(email="audit2@example.com")
    headers = _auth_headers(data)

    create = client.post(
        "/api/apps/",
        json={"name": "App Auditoria 2", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]

    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)

    logs = client.get(f"/api/audit-logs/?app_id={app_id}", headers=headers)
    entries = logs.json()
    status_logs = [e for e in entries if e["action"] == "update_app_status"]
    assert len(status_logs) == 1
    assert "draft -> published" in status_logs[0]["details"]


def test_update_app_content_logs_changed_fields(client, register_user):
    data = register_user(email="audit3@example.com")
    headers = _auth_headers(data)

    create = client.post(
        "/api/apps/",
        json={"name": "App Auditoria 3", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]

    client.put(f"/api/apps/{app_id}", json={"name": "Novo nome"}, headers=headers)

    logs = client.get(f"/api/audit-logs/?app_id={app_id}", headers=headers)
    entries = logs.json()
    update_logs = [e for e in entries if e["action"] == "update_app"]
    assert len(update_logs) == 1
    assert update_logs[0]["details"] == "name"


def test_delete_app_logs_entry_with_app_id_none(client, register_user):
    data = register_user(email="audit4@example.com")
    headers = _auth_headers(data)

    create = client.post(
        "/api/apps/",
        json={"name": "App Auditoria 4", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]

    client.delete(f"/api/apps/{app_id}", headers=headers)

    logs = client.get("/api/audit-logs/", headers=headers)
    entries = logs.json()
    delete_logs = [e for e in entries if e["action"] == "delete_app"]
    assert len(delete_logs) == 1
    assert delete_logs[0]["app_id"] is None
    assert f"app:{app_id}:" in delete_logs[0]["target"]


def test_order_status_update_logs_entry(client, register_user):
    data = register_user(email="audit5@example.com")
    headers = _auth_headers(data)

    create = client.post(
        "/api/apps/",
        json={"name": "App Auditoria 5", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)

    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Pizza", "price": 30.0},
        headers=headers,
    )
    item_id = item.json()["id"]

    checkout = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Cliente"}},
    )
    order_id = checkout.json()["id"]

    update = client.put(
        f"/api/apps/{app_id}/orders/{order_id}",
        json={"status": "confirmed"},
        headers=headers,
    )
    assert update.status_code == 200

    logs = client.get(f"/api/audit-logs/?app_id={app_id}", headers=headers)
    entries = logs.json()
    order_logs = [e for e in entries if e["action"] == "update_order_status"]
    assert len(order_logs) == 1
    assert "pending -> confirmed" in order_logs[0]["details"]
    assert order_logs[0]["target"] == f"order:{order_id}"


def test_2fa_enable_and_disable_log_entries(client, register_user):
    data = register_user(email="audit6@example.com")
    headers = _auth_headers(data)

    setup = client.post("/api/auth/2fa/setup", headers=headers)
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()
    client.post("/api/auth/2fa/enable", json={"code": code}, headers=headers)
    client.post("/api/auth/2fa/disable", json={"password": "senha12345"}, headers=headers)

    logs = client.get("/api/audit-logs/", headers=headers)
    actions = [e["action"] for e in logs.json()]
    assert "enable_2fa" in actions
    assert "disable_2fa" in actions


def test_confirm_billing_logs_plan_change(client, register_user):
    data = register_user(email="audit7@example.com")
    headers = _auth_headers(data)

    client.post("/api/billing/confirm", json={"plan": "pro"}, headers=headers)

    logs = client.get("/api/audit-logs/", headers=headers)
    entries = logs.json()
    billing_logs = [e for e in entries if e["action"] == "confirm_billing"]
    assert len(billing_logs) == 1
    assert "free -> pro" in billing_logs[0]["details"]


def test_audit_logs_are_isolated_per_owner(client, register_user):
    owner_a = register_user(email="audit8a@example.com")
    owner_b = register_user(email="audit8b@example.com")
    headers_a = _auth_headers(owner_a)
    headers_b = _auth_headers(owner_b)

    client.post(
        "/api/apps/",
        json={"name": "App do A", "description": "", "template_type": "other"},
        headers=headers_a,
    )

    logs_b = client.get("/api/audit-logs/", headers=headers_b)
    assert logs_b.json() == []


def test_audit_logs_requires_auth(client):
    response = client.get("/api/audit-logs/")
    assert response.status_code == 401
