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
