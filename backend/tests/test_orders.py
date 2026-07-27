from app.models import Order, OrderItem, ModuleItem, ItemVariation


def _published_app(client, register_user, email="orders@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Pedidos", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def test_create_order_fails_for_draft_app(client, register_user):
    data = register_user(email="ordersdraft@example.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Draft", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]

    response = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
    )
    assert response.status_code == 404


def test_create_order_is_public_and_persists(client, register_user, db_session):
    app_id, _ = _published_app(client, register_user)

    response = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente", "telefone": "11999999999"}},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["module_name"] == "formulario_delivery"

    order = db_session.query(Order).filter(Order.id == body["id"]).first()
    assert order is not None
    assert order.app_id == app_id


def test_list_and_update_order_requires_owner(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "ordersowner@example.com")
    client.post(
        f"/api/apps/{app_id}/modules/cotacao/orders",
        json={"data": {"nome": "Cliente"}},
    )

    other = register_user(email="ordersother@example.com")
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    forbidden = client.get(f"/api/apps/{app_id}/orders", headers=other_headers)
    assert forbidden.status_code == 404

    unauthenticated = client.get(f"/api/apps/{app_id}/orders")
    assert unauthenticated.status_code == 401

    listed = client.get(f"/api/apps/{app_id}/orders", headers=owner_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    order_id = listed.json()[0]["id"]

    updated = client.put(
        f"/api/apps/{app_id}/orders/{order_id}",
        json={"status": "confirmed"},
        headers=owner_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "confirmed"


def test_my_orders_requires_end_user_login(client, register_user):
    app_id, _ = _published_app(client, register_user, "ordersenduser@example.com")

    register_end_user = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": "cliente@example.com", "password": "senha12345", "full_name": "Cliente"},
    )
    assert register_end_user.status_code == 201
    end_user_token = register_end_user.json()["access_token"]
    end_user_headers = {"Authorization": f"Bearer {end_user_token}"}

    client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
        headers=end_user_headers,
    )

    no_auth = client.get(f"/api/apps/{app_id}/my-orders")
    assert no_auth.status_code == 401

    mine = client.get(f"/api/apps/{app_id}/my-orders", headers=end_user_headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 1


def test_update_order_status_notifies_end_user_without_crashing(client, register_user, db_session):
    """Sem SMTP/VAPID configurados, os hooks de notificação de status devem
    rodar em modo 'só log' e nunca quebrar a resposta da rota — mesmo
    comportamento já aceito do e-mail de novo pedido."""
    app_id, owner_headers = _published_app(client, register_user, "ordersnotify@example.com")

    register_end_user = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": "clientenotify@example.com", "password": "senha12345", "full_name": "Cliente"},
    )
    assert register_end_user.status_code == 201
    end_user_token = register_end_user.json()["access_token"]

    order = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
        headers={"Authorization": f"Bearer {end_user_token}"},
    )
    order_id = order.json()["id"]

    updated = client.put(
        f"/api/apps/{app_id}/orders/{order_id}",
        json={"status": "confirmed"},
        headers=owner_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "confirmed"


def _create_item(client, app_id, owner_headers, name="Pizza", price=30.0, stock=None):
    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": name, "price": price, "stock": stock},
        headers=owner_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_cart_checkout_creates_order_items_and_decrements_stock(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "cartstock@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Coxinha", price=8.0, stock=5)
    unlimited_id = _create_item(client, app_id, owner_headers, name="Refrigerante", price=6.0, stock=None)

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={
            "items": [{"item_id": item_id, "quantity": 2}, {"item_id": unlimited_id, "quantity": 3}],
            "customer": {"nome": "Cliente", "telefone": "11999999999"},
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["subtotal"] == 8.0 * 2 + 6.0 * 3
    assert body["amount"] == body["subtotal"]
    assert len(body["items"]) == 2

    order_items = db_session.query(OrderItem).filter(OrderItem.order_id == body["id"]).all()
    assert len(order_items) == 2
    assert {oi.name for oi in order_items} == {"Coxinha", "Refrigerante"}

    tracked_item = db_session.query(ModuleItem).filter(ModuleItem.id == item_id).first()
    assert tracked_item.stock == 3
    untracked_item = db_session.query(ModuleItem).filter(ModuleItem.id == unlimited_id).first()
    assert untracked_item.stock is None


def test_cart_checkout_uses_variation_price_and_stock(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "cartvariation@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Coxinha", price=8.0, stock=1)

    variation = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items/{item_id}/variations",
        json={"name": "Grande", "price": 12.0, "stock": 5},
        headers=owner_headers,
    )
    assert variation.status_code == 201
    variation_id = variation.json()["id"]

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={
            "items": [{"item_id": item_id, "variation_id": variation_id, "quantity": 2}],
            "customer": {"nome": "Cliente"},
        },
    )
    assert response.status_code == 201
    body = response.json()
    # preço vem da variação (12.0), não do item base (8.0); estoque checado é o
    # da variação (5), não o do item base (1) — item base ficaria sem estoque
    # suficiente se o backend confundisse os dois.
    assert body["subtotal"] == 12.0 * 2
    assert body["items"][0]["name"] == "Coxinha (Grande)"

    order_item = db_session.query(OrderItem).filter(OrderItem.order_id == body["id"]).first()
    assert order_item.item_variation_id == variation_id

    base_item = db_session.query(ModuleItem).filter(ModuleItem.id == item_id).first()
    assert base_item.stock == 1  # não decrementado — quem decrementa é a variação

    variation_row = db_session.query(ItemVariation).filter(ItemVariation.id == variation_id).first()
    assert variation_row.stock == 3  # 5 - 2


def test_cart_checkout_rejects_when_stock_insufficient(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "cartstockfail@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Bolo", price=20.0, stock=1)

    before_count = db_session.query(Order).filter(Order.app_id == app_id).count()

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 2}], "customer": {}},
    )
    assert response.status_code == 409

    after_count = db_session.query(Order).filter(Order.app_id == app_id).count()
    assert after_count == before_count
    unchanged_item = db_session.query(ModuleItem).filter(ModuleItem.id == item_id).first()
    assert unchanged_item.stock == 1


def test_cart_checkout_rejects_empty_cart(client, register_user):
    app_id, _ = _published_app(client, register_user, "cartempty@example.com")
    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [], "customer": {}},
    )
    assert response.status_code == 400


def _end_user_headers(client, app_id, email="cliente_cancel@example.com"):
    register_end_user = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": email, "password": "senha12345", "full_name": "Cliente"},
    )
    assert register_end_user.status_code == 201
    return {"Authorization": f"Bearer {register_end_user.json()['access_token']}"}


def test_order_has_status_event_timeline(client, register_user, db_session):
    """Todo pedido novo já nasce com um evento na linha do tempo (status
    inicial), e ganha um evento a mais a cada mudança feita pelo dono."""
    app_id, owner_headers = _published_app(client, register_user, "ordertimeline@example.com")
    end_user_headers = _end_user_headers(client, app_id, "timeline@example.com")

    created = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
        headers=end_user_headers,
    )
    assert created.status_code == 201
    assert len(created.json()["status_events"]) == 1
    assert created.json()["status_events"][0]["status"] == "pending"
    order_id = created.json()["id"]

    updated = client.put(
        f"/api/apps/{app_id}/orders/{order_id}",
        json={"status": "confirmed"},
        headers=owner_headers,
    )
    assert updated.status_code == 200
    events = updated.json()["status_events"]
    assert [e["status"] for e in events] == ["pending", "confirmed"]

    # reenviar o mesmo status não deve duplicar evento
    same_status = client.put(
        f"/api/apps/{app_id}/orders/{order_id}",
        json={"status": "confirmed"},
        headers=owner_headers,
    )
    assert len(same_status.json()["status_events"]) == 2


def test_customer_can_cancel_pending_order_but_not_after_preparing(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "ordercancel@example.com")
    end_user_headers = _end_user_headers(client, app_id, "cancel@example.com")

    order = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
        headers=end_user_headers,
    )
    order_id = order.json()["id"]

    cancelled = client.put(f"/api/apps/{app_id}/my-orders/{order_id}/cancel", headers=end_user_headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert [e["status"] for e in cancelled.json()["status_events"]] == ["pending", "cancelled"]

    other_order = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
        headers=end_user_headers,
    )
    other_order_id = other_order.json()["id"]
    client.put(
        f"/api/apps/{app_id}/orders/{other_order_id}",
        json={"status": "preparing"},
        headers=owner_headers,
    )

    too_late = client.put(f"/api/apps/{app_id}/my-orders/{other_order_id}/cancel", headers=end_user_headers)
    assert too_late.status_code == 400


def test_customer_cannot_cancel_another_customers_order(client, register_user):
    app_id, _ = _published_app(client, register_user, "ordercancelother@example.com")
    owner_of_order_headers = _end_user_headers(client, app_id, "dono_pedido@example.com")
    other_customer_headers = _end_user_headers(client, app_id, "outro_cliente@example.com")

    order = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Cliente"}},
        headers=owner_of_order_headers,
    )
    order_id = order.json()["id"]

    forbidden = client.put(f"/api/apps/{app_id}/my-orders/{order_id}/cancel", headers=other_customer_headers)
    assert forbidden.status_code == 404


def test_cart_checkout_rejects_invalid_gateway(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "cartgatewayinvalid@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Pizza", price=30.0)

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {}, "gateway": "boleto_magico"},
    )
    assert response.status_code == 400


def test_cart_checkout_with_gateway_fails_when_not_configured(client, register_user, db_session):
    """Sem access_token configurado no módulo mercado_pago, o checkout via
    carrinho falha com erro claro — mesma honestidade do fluxo de pagamento
    avulso em routes/payments.py."""
    app_id, owner_headers = _published_app(client, register_user, "cartgatewaynoconfig@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Pizza", price=30.0)

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {}, "gateway": "mercado_pago"},
    )
    assert response.status_code == 400


def test_cart_checkout_with_fake_gateway_credentials_returns_gateway_error(client, register_user, db_session):
    """Com access_token configurado mas inválido, a chamada real pra API do
    Mercado Pago retorna erro (502) — o Order do carrinho já foi criado com
    o valor real (não o 'valor' fixo do módulo) antes da tentativa."""
    app_id, owner_headers = _published_app(client, register_user, "cartgatewayfake@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Pizza", price=30.0)

    config = client.put(
        f"/api/apps/{app_id}/module-config/mercado_pago",
        json={"settings": {"access_token": "FAKE-TOKEN-INVALIDO"}},
        headers=owner_headers,
    )
    assert config.status_code == 200

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 2}], "customer": {"nome": "Cliente"}, "gateway": "mercado_pago"},
    )
    assert response.status_code == 502

    order = db_session.query(Order).filter(Order.app_id == app_id, Order.module_name == "cardapio").first()
    assert order is not None
    assert order.amount == 60.0
    assert order.payment_method == "mercado_pago"
    assert order.status == "pending"


def test_confirm_cart_order_payment_rejects_non_gateway_order(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "cartconfirmnongateway@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Pizza", price=30.0)

    order = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {}},
    )
    order_id = order.json()["id"]

    response = client.post(f"/api/apps/{app_id}/orders/{order_id}/confirm-payment")
    assert response.status_code == 400


def test_confirm_cart_order_payment_fails_for_missing_order(client, register_user):
    app_id, _ = _published_app(client, register_user, "cartconfirmmissing@example.com")

    response = client.post(f"/api/apps/{app_id}/orders/999999/confirm-payment")
    assert response.status_code == 404
