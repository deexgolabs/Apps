from app.models import Order


def _published_app(client, register_user, email="financial@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Financeiro", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def _checkout_and_set_status(client, app_id, owner_headers, item_id, status, fulfillment_type="delivery", gateway=None, quantity=1):
    payload = {
        "items": [{"item_id": item_id, "quantity": quantity}],
        "customer": {"nome": "Cliente"},
        "fulfillment_type": fulfillment_type,
    }
    if gateway:
        payload["gateway"] = gateway
    checkout = client.post(f"/api/apps/{app_id}/modules/cardapio/cart-checkout", json=payload)
    assert checkout.status_code == 201, checkout.text
    order_id = checkout.json()["id"]
    update = client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": status}, headers=owner_headers)
    assert update.status_code == 200, update.text
    return order_id


def test_financial_report_requires_access(client, register_user):
    app_id, _ = _published_app(client, register_user, "financialaccess@example.com")
    stranger = register_user(email="financialstranger@example.com")
    stranger_headers = {"Authorization": f"Bearer {stranger['access_token']}"}

    response = client.get(f"/api/apps/{app_id}/orders/financial-report", headers=stranger_headers)
    assert response.status_code == 404


def test_financial_report_empty_when_no_orders(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "financialempty@example.com")

    response = client.get(f"/api/apps/{app_id}/orders/financial-report", headers=owner_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_revenue"] == 0
    assert data["cancelled_count"] == 0
    assert data["by_fulfillment_type"] == []
    assert data["by_payment_method"] == []


def test_financial_report_aggregates_completed_and_cancelled(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "financialagg@example.com")
    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Bolo", "price": 20.0},
        headers=owner_headers,
    )
    item_id = item.json()["id"]

    _checkout_and_set_status(client, app_id, owner_headers, item_id, "completed", fulfillment_type="delivery")
    _checkout_and_set_status(client, app_id, owner_headers, item_id, "completed", fulfillment_type="pickup")
    _checkout_and_set_status(client, app_id, owner_headers, item_id, "cancelled", fulfillment_type="delivery")

    response = client.get(f"/api/apps/{app_id}/orders/financial-report", headers=owner_headers)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["total_revenue"] == 40.0
    assert data["cancelled_count"] == 1
    assert data["cancelled_value"] == 20.0

    fulfillment_by_key = {b["key"]: b for b in data["by_fulfillment_type"]}
    assert fulfillment_by_key["delivery"]["count"] == 1
    assert fulfillment_by_key["delivery"]["revenue"] == 20.0
    assert fulfillment_by_key["pickup"]["count"] == 1
    assert fulfillment_by_key["pickup"]["revenue"] == 20.0
    # Pedido cancelado não deve entrar na quebra por forma de entrega (só completed).
    assert sum(b["count"] for b in data["by_fulfillment_type"]) == 2


def test_financial_report_breaks_down_by_payment_method(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "financialpayment@example.com")
    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Bolo", "price": 15.0},
        headers=owner_headers,
    )
    item_id = item.json()["id"]

    _checkout_and_set_status(client, app_id, owner_headers, item_id, "completed")
    order_id = _checkout_and_set_status(client, app_id, owner_headers, item_id, "completed")
    # Simula um pedido pago via gateway sem depender de credencial real configurada
    # (o checkout de verdade por mercado_pago/paypal/pagseguro chama a API externa).
    order = db_session.query(Order).filter(Order.id == order_id).first()
    order.payment_method = "mercado_pago"
    db_session.commit()

    response = client.get(f"/api/apps/{app_id}/orders/financial-report", headers=owner_headers)
    data = response.json()
    payment_by_key = {b["key"]: b for b in data["by_payment_method"]}
    assert payment_by_key["pagamento_na_entrega"]["count"] == 1
    assert payment_by_key["mercado_pago"]["count"] == 1


def test_financial_export_csv_requires_access(client, register_user):
    app_id, _ = _published_app(client, register_user, "financialcsvaccess@example.com")
    stranger = register_user(email="financialcsvstranger@example.com")
    stranger_headers = {"Authorization": f"Bearer {stranger['access_token']}"}

    response = client.get(f"/api/apps/{app_id}/orders/financial-export.csv", headers=stranger_headers)
    assert response.status_code == 404


def test_financial_export_csv_returns_csv_content(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "financialcsv@example.com")
    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Bolo", "price": 10.0},
        headers=owner_headers,
    )
    item_id = item.json()["id"]
    _checkout_and_set_status(client, app_id, owner_headers, item_id, "completed")

    response = client.get(f"/api/apps/{app_id}/orders/financial-export.csv", headers=owner_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    assert "receita_total" in body
    assert "forma_entrega" in body
