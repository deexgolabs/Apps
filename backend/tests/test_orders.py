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


def _create_item(client, app_id, owner_headers, name="Pizza", price=30.0, stock=None, module_name="cardapio"):
    response = client.post(
        f"/api/apps/{app_id}/modules/{module_name}/items",
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


def _create_grouped_variation(client, app_id, owner_headers, item_id, name, price, group_name, stock=None):
    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items/{item_id}/variations",
        json={"name": name, "price": price, "group_name": group_name, "stock": stock},
        headers=owner_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_cart_checkout_combines_grouped_variations_as_delta_price(client, register_user, db_session):
    """Fase D: variações com group_name são somadas como delta ao preço base
    do item (não substituem, como no fluxo antigo de variação única) — o
    cliente escolhe uma opção de cada grupo (tamanho + sabor)."""
    app_id, owner_headers = _published_app(client, register_user, "combovariation@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Pizza", price=30.0)

    grande_id = _create_grouped_variation(client, app_id, owner_headers, item_id, "Grande", 10.0, "Tamanho", stock=5)
    _create_grouped_variation(client, app_id, owner_headers, item_id, "Pequena", 0.0, "Tamanho", stock=5)
    chocolate_id = _create_grouped_variation(client, app_id, owner_headers, item_id, "Chocolate", 5.0, "Sabor", stock=3)
    _create_grouped_variation(client, app_id, owner_headers, item_id, "Morango", 0.0, "Sabor", stock=3)

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={
            "items": [{"item_id": item_id, "variation_ids": [grande_id, chocolate_id], "quantity": 1}],
            "customer": {"nome": "Cliente"},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    # 30 (base) + 10 (Grande) + 5 (Chocolate) = 45
    assert body["subtotal"] == 45.0
    assert "Grande" in body["items"][0]["name"]
    assert "Chocolate" in body["items"][0]["name"]

    grande = db_session.query(ItemVariation).filter(ItemVariation.id == grande_id).first()
    chocolate = db_session.query(ItemVariation).filter(ItemVariation.id == chocolate_id).first()
    assert grande.stock == 4  # decrementado
    assert chocolate.stock == 2  # decrementado
    base_item = db_session.query(ModuleItem).filter(ModuleItem.id == item_id).first()
    assert base_item.stock is None  # item base sem estoque próprio não é mexido


def test_cart_checkout_rejects_two_selections_from_same_group(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "combogroupclash@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Pizza", price=30.0)

    grande_id = _create_grouped_variation(client, app_id, owner_headers, item_id, "Grande", 10.0, "Tamanho")
    media_id = _create_grouped_variation(client, app_id, owner_headers, item_id, "Média", 5.0, "Tamanho")

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={
            "items": [{"item_id": item_id, "variation_ids": [grande_id, media_id], "quantity": 1}],
            "customer": {},
        },
    )
    assert response.status_code == 400


def test_cart_checkout_rejects_combo_with_insufficient_stock(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "combostock@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Pizza", price=30.0)

    grande_id = _create_grouped_variation(client, app_id, owner_headers, item_id, "Grande", 10.0, "Tamanho", stock=1)
    chocolate_id = _create_grouped_variation(client, app_id, owner_headers, item_id, "Chocolate", 5.0, "Sabor", stock=3)

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={
            "items": [{"item_id": item_id, "variation_ids": [grande_id, chocolate_id], "quantity": 2}],
            "customer": {},
        },
    )
    assert response.status_code == 409

    grande = db_session.query(ItemVariation).filter(ItemVariation.id == grande_id).first()
    assert grande.stock == 1  # não decrementado — checkout inteiro falhou


def test_sales_report_computes_revenue_status_and_top_products(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "salesreport@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Pizza", price=30.0)

    order1 = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 2}], "customer": {}},
    )
    order2 = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {}},
    )
    assert order1.status_code == 201 and order2.status_code == 201

    client.put(f"/api/apps/{app_id}/orders/{order1.json()['id']}", json={"status": "completed"}, headers=owner_headers)

    report = client.get(f"/api/apps/{app_id}/orders/report", headers=owner_headers)
    assert report.status_code == 200
    body = report.json()
    assert body["revenue"] == 60.0  # só o pedido completed (2x30)
    assert body["orders_by_status"] == {"completed": 1, "pending": 1}
    assert body["top_products"][0]["name"] == "Pizza"
    assert body["top_products"][0]["quantity"] == 3  # soma dos dois pedidos


def test_sales_report_requires_owner(client, register_user):
    app_id, _ = _published_app(client, register_user, "salesreportauth@example.com")
    other = register_user(email="salesreportother@example.com")
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    response = client.get(f"/api/apps/{app_id}/orders/report", headers=other_headers)
    assert response.status_code == 404


def test_export_orders_csv_returns_csv_content(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "exportcsv@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Pizza", price=30.0)
    client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Cliente"}},
    )

    response = client.get(f"/api/apps/{app_id}/orders/export.csv", headers=owner_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "Pizza" in response.text


def test_close_table_marks_open_dine_in_orders_as_completed(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "closetable@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Pizza", price=30.0)

    order = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={
            "items": [{"item_id": item_id, "quantity": 1}],
            "customer": {},
            "fulfillment_type": "dine_in",
            "table_number": "5",
        },
    )
    assert order.status_code == 201
    assert order.json()["table_number"] == "5"

    close = client.put(f"/api/apps/{app_id}/orders/close-table", json={"table_number": "5"}, headers=owner_headers)
    assert close.status_code == 200
    assert close.json()[0]["status"] == "completed"

    updated_order = db_session.query(Order).filter(Order.id == order.json()["id"]).first()
    assert updated_order.status == "completed"


def test_close_table_returns_404_when_no_open_orders(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "closetableempty@example.com")

    response = client.put(f"/api/apps/{app_id}/orders/close-table", json={"table_number": "99"}, headers=owner_headers)
    assert response.status_code == 404


def test_unlocked_items_reflects_confirmed_purchase_only(client, register_user, db_session):
    """Paywall: um item só aparece em unlocked-items depois que o pedido do
    cliente que o comprou passa a status confirmed — pending não desbloqueia."""
    app_id, owner_headers = _published_app(client, register_user, "paywallunlock@example.com")
    item_id = _create_item(
        client, app_id, owner_headers, name="Artigo Exclusivo", price=15.0, stock=None, module_name="conteudo_pago"
    )
    end_user_headers = _end_user_headers(client, app_id, "assinante@example.com")

    checkout = client.post(
        f"/api/apps/{app_id}/modules/conteudo_pago/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}]},
        headers=end_user_headers,
    )
    assert checkout.status_code == 201
    order_id = checkout.json()["id"]

    still_locked = client.get(
        f"/api/apps/{app_id}/modules/conteudo_pago/unlocked-items", headers=end_user_headers
    )
    assert still_locked.status_code == 200
    assert still_locked.json() == []

    confirm = client.put(
        f"/api/apps/{app_id}/orders/{order_id}", json={"status": "confirmed"}, headers=owner_headers
    )
    assert confirm.status_code == 200

    unlocked = client.get(
        f"/api/apps/{app_id}/modules/conteudo_pago/unlocked-items", headers=end_user_headers
    )
    assert unlocked.status_code == 200
    assert unlocked.json() == [item_id]


def test_unlocked_items_requires_end_user_login(client, register_user):
    app_id, _ = _published_app(client, register_user, "paywallnoauth@example.com")
    response = client.get(f"/api/apps/{app_id}/modules/conteudo_pago/unlocked-items")
    assert response.status_code in (401, 403)


def test_unlocked_items_isolated_per_end_user(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "paywallisolation@example.com")
    item_id = _create_item(
        client, app_id, owner_headers, name="Artigo B", price=10.0, stock=None, module_name="conteudo_pago"
    )
    buyer_headers = _end_user_headers(client, app_id, "comprador@example.com")
    other_headers = _end_user_headers(client, app_id, "outro_cliente@example.com")

    checkout = client.post(
        f"/api/apps/{app_id}/modules/conteudo_pago/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}]},
        headers=buyer_headers,
    )
    order_id = checkout.json()["id"]
    client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": "confirmed"}, headers=owner_headers)

    buyer_view = client.get(f"/api/apps/{app_id}/modules/conteudo_pago/unlocked-items", headers=buyer_headers)
    assert buyer_view.json() == [item_id]

    other_view = client.get(f"/api/apps/{app_id}/modules/conteudo_pago/unlocked-items", headers=other_headers)
    assert other_view.json() == []


def test_cart_checkout_persists_pickup_point_and_delivery_slot(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "pickupslot@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Bolo", price=20.0, stock=None)

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={
            "items": [{"item_id": item_id, "quantity": 1}],
            "customer": {"nome": "Cliente"},
            "fulfillment_type": "pickup",
            "pickup_point": "Loja Centro: Rua A, 123",
            "delivery_slot": "Hoje 18:00-19:00",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["pickup_point"] == "Loja Centro: Rua A, 123"
    assert body["delivery_slot"] == "Hoje 18:00-19:00"

    order = db_session.query(Order).filter(Order.id == body["id"]).first()
    assert order.pickup_point == "Loja Centro: Rua A, 123"
    assert order.delivery_slot == "Hoje 18:00-19:00"


def test_cart_checkout_ignores_pickup_point_when_not_pickup(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "pickupignored@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Bolo", price=20.0, stock=None)

    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={
            "items": [{"item_id": item_id, "quantity": 1}],
            "customer": {"nome": "Cliente"},
            "fulfillment_type": "delivery",
            "pickup_point": "Loja Centro: Rua A, 123",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["pickup_point"] is None
