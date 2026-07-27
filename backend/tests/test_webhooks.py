from app.models import Order
import app.routes.orders as orders_module


def _published_app(client, register_user, email="webhooks@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Webhooks", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def _create_item(client, app_id, headers, name="Pizza", price=30.0):
    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": name, "price": price},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _cart_checkout_with_gateway(client, app_id, item_id, gateway, monkeypatch, gateway_order_id="GATEWAY-ORDER-123"):
    """Sempre stuba a criação da cobrança na gateway — nunca depende de rede
    real, igual ao verify_* nos testes de webhook. Devolve (order, response)."""

    async def fake_checkout_mercado_pago(valor, titulo, access_token, external_reference=None, notification_url=None):
        return {"checkout_url": "https://mercadopago.example/checkout"}

    async def fake_checkout_pagseguro(valor, titulo, token, notification_url=None):
        return {"checkout_url": "https://pagseguro.example/checkout", "gateway_order_id": gateway_order_id}

    monkeypatch.setattr(orders_module, "checkout_mercado_pago", fake_checkout_mercado_pago)
    monkeypatch.setattr(orders_module, "checkout_pagseguro", fake_checkout_pagseguro)

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Cliente"}, "gateway": gateway},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_mercado_pago_webhook_confirms_order_when_approved(client, register_user, db_session, monkeypatch):
    app_id, headers = _published_app(client, register_user, "webhookmpapproved@example.com")
    item_id = _create_item(client, app_id, headers)
    client.put(
        f"/api/apps/{app_id}/module-config/mercado_pago",
        json={"settings": {"access_token": "FAKE-TOKEN"}},
        headers=headers,
    )
    order = _cart_checkout_with_gateway(client, app_id, item_id, "mercado_pago", monkeypatch)
    assert order["status"] == "pending"

    async def fake_verify(external_reference, access_token):
        assert access_token == "FAKE-TOKEN"
        return True

    monkeypatch.setattr(orders_module, "verify_mercado_pago", fake_verify)

    response = client.post(f"/api/apps/{app_id}/webhooks/mercado_pago?order_id={order['id']}")
    assert response.status_code == 200
    assert response.json() == {"received": True}

    updated = db_session.query(Order).filter(Order.id == order["id"]).first()
    assert updated.status == "confirmed"


def test_mercado_pago_webhook_does_nothing_when_not_approved(client, register_user, db_session, monkeypatch):
    app_id, headers = _published_app(client, register_user, "webhookmpnotapproved@example.com")
    item_id = _create_item(client, app_id, headers)
    client.put(
        f"/api/apps/{app_id}/module-config/mercado_pago",
        json={"settings": {"access_token": "FAKE-TOKEN"}},
        headers=headers,
    )
    order = _cart_checkout_with_gateway(client, app_id, item_id, "mercado_pago", monkeypatch)

    async def fake_verify(external_reference, access_token):
        return False

    monkeypatch.setattr(orders_module, "verify_mercado_pago", fake_verify)

    response = client.post(f"/api/apps/{app_id}/webhooks/mercado_pago?order_id={order['id']}")
    assert response.status_code == 200

    updated = db_session.query(Order).filter(Order.id == order["id"]).first()
    assert updated.status == "pending"


def test_webhook_ignores_unknown_order_id(client, register_user):
    app_id, _ = _published_app(client, register_user, "webhookunknown@example.com")

    response = client.post(f"/api/apps/{app_id}/webhooks/mercado_pago?order_id=999999")
    assert response.status_code == 200
    assert response.json() == {"received": True}


def test_webhook_ignores_unknown_gateway(client, register_user):
    app_id, _ = _published_app(client, register_user, "webhookbadgateway@example.com")

    response = client.post(f"/api/apps/{app_id}/webhooks/not_a_real_gateway?order_id=1")
    assert response.status_code == 200
    assert response.json() == {"received": True}


def test_mercado_pago_webhook_does_not_reconfirm_already_confirmed_order(client, register_user, db_session, monkeypatch):
    app_id, headers = _published_app(client, register_user, "webhookalreadyconfirmed@example.com")
    item_id = _create_item(client, app_id, headers)
    client.put(
        f"/api/apps/{app_id}/module-config/mercado_pago",
        json={"settings": {"access_token": "FAKE-TOKEN"}},
        headers=headers,
    )
    order = _cart_checkout_with_gateway(client, app_id, item_id, "mercado_pago", monkeypatch)

    call_count = 0

    async def fake_verify(external_reference, access_token):
        nonlocal call_count
        call_count += 1
        return True

    monkeypatch.setattr(orders_module, "verify_mercado_pago", fake_verify)

    client.post(f"/api/apps/{app_id}/webhooks/mercado_pago?order_id={order['id']}")
    assert call_count == 1

    # segunda notificação (comum em gateways, que reenviam) não deve reprocessar
    client.post(f"/api/apps/{app_id}/webhooks/mercado_pago?order_id={order['id']}")
    assert call_count == 1

    listed = client.get(f"/api/apps/{app_id}/orders", headers=headers)
    found = next(o for o in listed.json() if o["id"] == order["id"])
    assert len([e for e in found["status_events"] if e["status"] == "confirmed"]) == 1


def test_paypal_webhook_confirms_order_via_resource_id(client, register_user, db_session, monkeypatch):
    app_id, headers = _published_app(client, register_user, "webhookpaypal@example.com")
    item_id = _create_item(client, app_id, headers)
    client.put(
        f"/api/apps/{app_id}/module-config/paypal",
        json={"settings": {"client_id": "FAKE-ID", "client_secret": "FAKE-SECRET"}},
        headers=headers,
    )

    async def fake_checkout_paypal(valor, titulo, client_id, client_secret):
        return {"checkout_url": "https://paypal.example/approve", "gateway_order_id": "PAYPAL-ORDER-123"}

    monkeypatch.setattr(orders_module, "checkout_paypal", fake_checkout_paypal)

    order = _cart_checkout_with_gateway(client, app_id, item_id, "paypal", monkeypatch)
    assert order["status"] == "pending"

    updated = db_session.query(Order).filter(Order.id == order["id"]).first()
    assert updated.payment_reference == "PAYPAL-ORDER-123"

    async def fake_verify_paypal(paypal_order_id, client_id, client_secret):
        assert paypal_order_id == "PAYPAL-ORDER-123"
        return True

    monkeypatch.setattr(orders_module, "verify_paypal", fake_verify_paypal)

    response = client.post(
        f"/api/apps/{app_id}/webhooks/paypal",
        json={"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": "PAYPAL-ORDER-123"}},
    )
    assert response.status_code == 200

    db_session.refresh(updated)
    assert updated.status == "confirmed"
