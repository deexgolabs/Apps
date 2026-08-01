from datetime import timedelta

from app.models import Order, utcnow


def _published_app(client, register_user, email="rfm@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App RFM", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def _end_user_headers_and_id(client, app_id, email):
    register = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": email, "password": "senha12345", "full_name": email.split("@")[0]},
    )
    assert register.status_code == 201, register.text
    data = register.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["id"]


def _buy_and_complete(client, db_session, app_id, owner_headers, buyer_headers, days_ago=0, price=20.0):
    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Bolo", "price": price},
        headers=owner_headers,
    )
    item_id = item.json()["id"]
    checkout = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Cliente"}},
        headers=buyer_headers,
    )
    assert checkout.status_code == 201, checkout.text
    order_id = checkout.json()["id"]
    update = client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": "completed"}, headers=owner_headers)
    assert update.status_code == 200, update.text

    if days_ago:
        order = db_session.query(Order).filter(Order.id == order_id).first()
        order.created_at = utcnow() - timedelta(days=days_ago)
        db_session.commit()

    return order_id


def test_rfm_requires_access(client, register_user):
    app_id, _ = _published_app(client, register_user, "rfmaccess@example.com")
    stranger = register_user(email="rfmstranger@example.com")
    stranger_headers = {"Authorization": f"Bearer {stranger['access_token']}"}

    response = client.get(f"/api/apps/{app_id}/rfm", headers=stranger_headers)
    assert response.status_code == 404


def test_customer_with_no_orders_is_excluded(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "rfmnoorders@example.com")
    _end_user_headers_and_id(client, app_id, "noorder@example.com")

    response = client.get(f"/api/apps/{app_id}/rfm", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["customers"] == []


def test_single_recent_order_is_tier_novo(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "rfmnovo@example.com")
    buyer_headers, buyer_id = _end_user_headers_and_id(client, app_id, "novo@example.com")
    _buy_and_complete(client, db_session, app_id, owner_headers, buyer_headers)

    response = client.get(f"/api/apps/{app_id}/rfm", headers=owner_headers)
    assert response.status_code == 200
    customers = {c["end_user_id"]: c for c in response.json()["customers"]}
    assert customers[buyer_id]["tier"] == "novo"
    assert customers[buyer_id]["frequency"] == 1
    assert customers[buyer_id]["monetary"] == 20.0


def test_three_recent_orders_is_tier_campeao(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "rfmcampeao@example.com")
    buyer_headers, buyer_id = _end_user_headers_and_id(client, app_id, "campeao@example.com")
    for _ in range(3):
        _buy_and_complete(client, db_session, app_id, owner_headers, buyer_headers)

    response = client.get(f"/api/apps/{app_id}/rfm", headers=owner_headers)
    customers = {c["end_user_id"]: c for c in response.json()["customers"]}
    assert customers[buyer_id]["tier"] == "campeao"
    assert customers[buyer_id]["frequency"] == 3
    assert customers[buyer_id]["monetary"] == 60.0


def test_frequent_but_old_orders_is_tier_em_risco(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "rfmemrisco@example.com")
    buyer_headers, buyer_id = _end_user_headers_and_id(client, app_id, "emrisco@example.com")
    _buy_and_complete(client, db_session, app_id, owner_headers, buyer_headers, days_ago=120)
    _buy_and_complete(client, db_session, app_id, owner_headers, buyer_headers, days_ago=100)

    response = client.get(f"/api/apps/{app_id}/rfm", headers=owner_headers)
    customers = {c["end_user_id"]: c for c in response.json()["customers"]}
    assert customers[buyer_id]["tier"] == "em_risco"
    assert customers[buyer_id]["frequency"] == 2


def test_very_old_order_is_tier_perdido(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "rfmperdido@example.com")
    buyer_headers, buyer_id = _end_user_headers_and_id(client, app_id, "perdido@example.com")
    _buy_and_complete(client, db_session, app_id, owner_headers, buyer_headers, days_ago=200)

    response = client.get(f"/api/apps/{app_id}/rfm", headers=owner_headers)
    customers = {c["end_user_id"]: c for c in response.json()["customers"]}
    assert customers[buyer_id]["tier"] == "perdido"


def test_tier_counts_matches_customers(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "rfmcounts@example.com")
    buyer_headers, _ = _end_user_headers_and_id(client, app_id, "counts1@example.com")
    _buy_and_complete(client, db_session, app_id, owner_headers, buyer_headers)

    response = client.get(f"/api/apps/{app_id}/rfm", headers=owner_headers)
    data = response.json()
    assert data["tier_counts"]["novo"] == 1
    assert sum(data["tier_counts"].values()) == len(data["customers"])
