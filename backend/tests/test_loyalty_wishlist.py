from app.models import LoyaltyAccount, WishlistItem


def _published_app(client, register_user, email="loyalty@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Fidelidade", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def _end_user_headers(client, app_id, email="cliente_loyalty@example.com"):
    register_end_user = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": email, "password": "senha12345", "full_name": "Cliente"},
    )
    assert register_end_user.status_code == 201
    return {"Authorization": f"Bearer {register_end_user.json()['access_token']}"}


def _create_item(client, app_id, owner_headers, name="Pizza", price=30.0):
    response = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": name, "price": price},
        headers=owner_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _set_pontos_por_real(client, app_id, owner_headers, pontos_por_real):
    response = client.put(
        f"/api/apps/{app_id}/module-config/cartao_fidelidade",
        json={"settings": {"pontos_por_real": pontos_por_real}},
        headers=owner_headers,
    )
    assert response.status_code == 200


def test_completed_order_credits_loyalty_points(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "loyaltycredit@example.com")
    _set_pontos_por_real(client, app_id, owner_headers, 1)
    end_user_headers = _end_user_headers(client, app_id, "cliente_credit@example.com")
    item_id = _create_item(client, app_id, owner_headers, price=30.0)

    order = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 2}], "customer": {"nome": "Cliente"}},
        headers=end_user_headers,
    )
    assert order.status_code == 201
    order_id = order.json()["id"]

    balance_before = client.get(f"/api/apps/{app_id}/loyalty/me", headers=end_user_headers)
    assert balance_before.json()["points"] == 0

    updated = client.put(
        f"/api/apps/{app_id}/orders/{order_id}",
        json={"status": "completed"},
        headers=owner_headers,
    )
    assert updated.status_code == 200

    balance_after = client.get(f"/api/apps/{app_id}/loyalty/me", headers=end_user_headers)
    assert balance_after.json()["points"] == 60

    account = db_session.query(LoyaltyAccount).filter(LoyaltyAccount.app_id == app_id).first()
    assert account.points == 60


def test_loyalty_points_not_credited_twice_for_same_order(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "loyaltytwice@example.com")
    _set_pontos_por_real(client, app_id, owner_headers, 1)
    end_user_headers = _end_user_headers(client, app_id, "cliente_twice@example.com")
    item_id = _create_item(client, app_id, owner_headers, price=10.0)

    order = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Cliente"}},
        headers=end_user_headers,
    )
    order_id = order.json()["id"]

    client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": "completed"}, headers=owner_headers)
    # reenviar o mesmo status "completed" não deve creditar de novo
    client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": "completed"}, headers=owner_headers)

    balance = client.get(f"/api/apps/{app_id}/loyalty/me", headers=end_user_headers)
    assert balance.json()["points"] == 10


def test_loyalty_points_not_credited_without_pontos_por_real_configured(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "loyaltynoconfig@example.com")
    end_user_headers = _end_user_headers(client, app_id, "cliente_noconfig@example.com")
    item_id = _create_item(client, app_id, owner_headers, price=10.0)

    order = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Cliente"}},
        headers=end_user_headers,
    )
    order_id = order.json()["id"]

    client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": "completed"}, headers=owner_headers)

    balance = client.get(f"/api/apps/{app_id}/loyalty/me", headers=end_user_headers)
    assert balance.json()["points"] == 0


def test_loyalty_points_isolated_between_customers(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "loyaltyisolation@example.com")
    _set_pontos_por_real(client, app_id, owner_headers, 2)
    item_id = _create_item(client, app_id, owner_headers, price=10.0)

    headers_a = _end_user_headers(client, app_id, "cliente_a@example.com")
    headers_b = _end_user_headers(client, app_id, "cliente_b@example.com")

    order_a = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "A"}},
        headers=headers_a,
    ).json()

    client.put(f"/api/apps/{app_id}/orders/{order_a['id']}", json={"status": "completed"}, headers=owner_headers)

    assert client.get(f"/api/apps/{app_id}/loyalty/me", headers=headers_a).json()["points"] == 20
    assert client.get(f"/api/apps/{app_id}/loyalty/me", headers=headers_b).json()["points"] == 0


def test_owner_can_list_loyalty_customers_ranked_by_points(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "loyaltylist@example.com")
    _set_pontos_por_real(client, app_id, owner_headers, 1)
    item_id = _create_item(client, app_id, owner_headers, price=10.0)

    headers_a = _end_user_headers(client, app_id, "cliente_list_a@example.com")
    headers_b = _end_user_headers(client, app_id, "cliente_list_b@example.com")

    order_a = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 3}], "customer": {"nome": "A"}},
        headers=headers_a,
    ).json()
    order_b = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "B"}},
        headers=headers_b,
    ).json()
    client.put(f"/api/apps/{app_id}/orders/{order_a['id']}", json={"status": "completed"}, headers=owner_headers)
    client.put(f"/api/apps/{app_id}/orders/{order_b['id']}", json={"status": "completed"}, headers=owner_headers)

    listing = client.get(f"/api/apps/{app_id}/loyalty", headers=owner_headers)
    assert listing.status_code == 200
    rows = listing.json()
    assert [r["points"] for r in rows] == [30, 10]

    other = register_user(email="loyaltylistother@example.com")
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    forbidden = client.get(f"/api/apps/{app_id}/loyalty", headers=other_headers)
    assert forbidden.status_code == 404


def test_wishlist_add_list_and_remove(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "wishlistcrud@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Sushi", price=45.0)
    end_user_headers = _end_user_headers(client, app_id, "cliente_wishlist@example.com")

    added = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items/{item_id}/wishlist",
        headers=end_user_headers,
    )
    assert added.status_code == 200
    assert added.json()["item_id"] == item_id

    listing = client.get(f"/api/apps/{app_id}/wishlist/me", headers=end_user_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    removed = client.delete(f"/api/apps/{app_id}/wishlist/{item_id}", headers=end_user_headers)
    assert removed.status_code == 204

    listing_after = client.get(f"/api/apps/{app_id}/wishlist/me", headers=end_user_headers)
    assert listing_after.json() == []

    assert db_session.query(WishlistItem).filter(WishlistItem.app_id == app_id).count() == 0


def test_wishlist_add_is_idempotent(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "wishlistidempotent@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Sushi", price=45.0)
    end_user_headers = _end_user_headers(client, app_id, "cliente_idempotent@example.com")

    first = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items/{item_id}/wishlist",
        headers=end_user_headers,
    )
    second = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items/{item_id}/wishlist",
        headers=end_user_headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    listing = client.get(f"/api/apps/{app_id}/wishlist/me", headers=end_user_headers)
    assert len(listing.json()) == 1


def test_wishlist_requires_end_user_login(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "wishlistauth@example.com")
    item_id = _create_item(client, app_id, owner_headers, name="Sushi", price=45.0)

    response = client.post(f"/api/apps/{app_id}/modules/cardapio/items/{item_id}/wishlist")
    assert response.status_code == 401

    no_auth_list = client.get(f"/api/apps/{app_id}/wishlist/me")
    assert no_auth_list.status_code == 401


def test_wishlist_remove_missing_item_returns_404(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "wishlistremove404@example.com")
    end_user_headers = _end_user_headers(client, app_id, "cliente_remove404@example.com")

    response = client.delete(f"/api/apps/{app_id}/wishlist/999999", headers=end_user_headers)
    assert response.status_code == 404
