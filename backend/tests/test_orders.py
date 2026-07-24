from app.models import Order


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
