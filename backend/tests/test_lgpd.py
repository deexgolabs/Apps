def _published_app(client, register_user, email="lojista@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App LGPD", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def _register_end_user(client, app_id, email="cliente@example.com", password="senha12345"):
    response = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": email, "password": password, "full_name": "Cliente Teste"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_export_my_data_returns_empty_collections_for_new_user(client, register_user):
    app_id, _ = _published_app(client, register_user, "lgpd1@example.com")
    token = _register_end_user(client, app_id, "cliente1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/api/apps/{app_id}/end-users/me/export", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["email"] == "cliente1@example.com"
    assert body["orders"] == []
    assert body["reviews"] == []
    assert body["wishlist"] == []
    assert body["loyalty_points"] == 0


def test_export_my_data_includes_own_orders_and_wishlist(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "lgpd2@example.com")
    token = _register_end_user(client, app_id, "cliente2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Pizza", "price": 30.0},
        headers=owner_headers,
    )
    item_id = item.json()["id"]

    checkout = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Cliente"}},
        headers=headers,
    )
    assert checkout.status_code == 201

    wishlist = client.post(f"/api/apps/{app_id}/modules/cardapio/items/{item_id}/wishlist", headers=headers)
    assert wishlist.status_code in (200, 201)

    response = client.get(f"/api/apps/{app_id}/end-users/me/export", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["orders"]) == 1
    assert body["orders"][0]["end_user_id"] == checkout.json()["end_user_id"]
    assert len(body["wishlist"]) == 1
    assert body["wishlist"][0]["item_id"] == item_id


def test_export_my_data_requires_auth(client, register_user):
    app_id, _ = _published_app(client, register_user, "lgpd3@example.com")

    response = client.get(f"/api/apps/{app_id}/end-users/me/export")
    assert response.status_code == 401


def test_delete_my_account_anonymizes_profile(client, register_user, db_session):
    from app.models import AppUser

    app_id, _ = _published_app(client, register_user, "lgpd4@example.com")
    token = _register_end_user(client, app_id, "cliente4@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete(f"/api/apps/{app_id}/end-users/me", headers=headers)
    assert response.status_code == 200

    db_user = db_session.query(AppUser).filter(AppUser.email.like("removido-%")).first()
    assert db_user is not None
    assert db_user.full_name == "Usuário removido"
    assert db_user.phone is None
    assert db_user.address is None
    assert db_user.password_hash is None
    assert db_user.deleted_at is not None


def test_deleted_end_user_token_no_longer_authenticates(client, register_user):
    app_id, _ = _published_app(client, register_user, "lgpd5@example.com")
    token = _register_end_user(client, app_id, "cliente5@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.delete(f"/api/apps/{app_id}/end-users/me", headers=headers)

    me = client.get(f"/api/apps/{app_id}/end-users/me", headers=headers)
    assert me.status_code == 401


def test_deleted_end_user_cannot_login_with_old_credentials(client, register_user):
    app_id, _ = _published_app(client, register_user, "lgpd6@example.com")
    token = _register_end_user(client, app_id, "cliente6@example.com", "senha12345")
    headers = {"Authorization": f"Bearer {token}"}

    client.delete(f"/api/apps/{app_id}/end-users/me", headers=headers)

    login = client.post(
        f"/api/apps/{app_id}/end-users/login",
        json={"email": "cliente6@example.com", "password": "senha12345"},
    )
    assert login.status_code == 401


def test_delete_my_account_requires_auth(client, register_user):
    app_id, _ = _published_app(client, register_user, "lgpd7@example.com")

    response = client.delete(f"/api/apps/{app_id}/end-users/me")
    assert response.status_code == 401
