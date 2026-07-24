from app.models import Order


def _published_app(client, register_user, email="payments@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Pagamentos", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def test_checkout_rejects_invalid_module(client, register_user):
    app_id, _ = _published_app(client, register_user)

    response = client.post(f"/api/apps/{app_id}/modules/whatsapp/checkout")
    assert response.status_code == 400


def test_checkout_fails_when_gateway_not_configured(client, register_user):
    """Sem access_token configurado no módulo, o checkout falha com erro claro
    e nenhum Order é criado — mesma honestidade já usada pra billing/Mercado Livre."""
    app_id, _ = _published_app(client, register_user, "paymentsnoconfig@example.com")

    response = client.post(f"/api/apps/{app_id}/modules/mercado_pago/checkout")
    assert response.status_code == 400


def test_checkout_with_fake_credentials_returns_gateway_error(client, register_user, db_session):
    """Com access_token configurado mas inválido, a chamada de verdade pra API do
    Mercado Pago retorna um erro real da gateway (502) — não um crash, não um
    sucesso fingido. Confirma também que o Order foi criado antes da tentativa."""
    app_id, headers = _published_app(client, register_user, "paymentsfake@example.com")

    config = client.put(
        f"/api/apps/{app_id}/module-config/mercado_pago",
        json={"settings": {"titulo": "Sinal", "valor": "50.00", "access_token": "FAKE-TOKEN-INVALIDO"}},
        headers=headers,
    )
    assert config.status_code == 200

    response = client.post(f"/api/apps/{app_id}/modules/mercado_pago/checkout")
    assert response.status_code == 502

    order = db_session.query(Order).filter(Order.app_id == app_id, Order.module_name == "mercado_pago").first()
    assert order is not None
    assert order.status == "pending"


def test_confirm_rejects_invalid_module(client, register_user):
    app_id, _ = _published_app(client, register_user, "paymentsconfirm@example.com")

    response = client.post(f"/api/apps/{app_id}/modules/whatsapp/orders/1/confirm")
    assert response.status_code == 400


def test_confirm_fails_for_missing_order(client, register_user):
    app_id, _ = _published_app(client, register_user, "paymentsmissing@example.com")

    response = client.post(f"/api/apps/{app_id}/modules/mercado_pago/orders/999999/confirm")
    assert response.status_code == 404
