from app.models import Coupon, User


def _published_app(client, register_user, email="coupons@example.com", plan="pro"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Cupons", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers, data["user"]["id"]


def _set_plan(db_session, user_id, plan):
    user = db_session.query(User).filter(User.id == user_id).first()
    user.plan = plan
    db_session.commit()


def test_coupon_blocked_on_free_plan(client, register_user, db_session):
    app_id, headers, user_id = _published_app(client, register_user, "couponsfree@example.com")
    _set_plan(db_session, user_id, "free")

    response = client.post(
        f"/api/apps/{app_id}/coupons",
        json={"code": "PROMO10", "discount_type": "percent", "discount_value": 10},
        headers=headers,
    )
    assert response.status_code == 403


def test_coupon_crud_for_pro_plan(client, register_user, db_session):
    app_id, headers, user_id = _published_app(client, register_user, "couponspro@example.com")
    _set_plan(db_session, user_id, "pro")

    created = client.post(
        f"/api/apps/{app_id}/coupons",
        json={"code": "promo10", "discount_type": "percent", "discount_value": 10},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["code"] == "PROMO10"
    coupon_id = created.json()["id"]

    listed = client.get(f"/api/apps/{app_id}/coupons", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(f"/api/apps/{app_id}/coupons/{coupon_id}", json={"active": False}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["active"] is False

    deleted = client.delete(f"/api/apps/{app_id}/coupons/{coupon_id}", headers=headers)
    assert deleted.status_code == 204
    assert db_session.query(Coupon).filter(Coupon.id == coupon_id).first() is None


def test_validate_coupon_percent_and_fixed(client, register_user, db_session):
    app_id, headers, user_id = _published_app(client, register_user, "couponsvalidate@example.com")
    _set_plan(db_session, user_id, "pro")

    client.post(
        f"/api/apps/{app_id}/coupons",
        json={"code": "PERC10", "discount_type": "percent", "discount_value": 10},
        headers=headers,
    )
    client.post(
        f"/api/apps/{app_id}/coupons",
        json={"code": "FIXO5", "discount_type": "fixed", "discount_value": 5},
        headers=headers,
    )

    percent = client.post(f"/api/apps/{app_id}/public/coupons/validate", json={"code": "perc10", "subtotal": 100})
    assert percent.status_code == 200
    assert percent.json() == {"valid": True, "discount_amount": 10.0, "reason": None}

    fixed = client.post(f"/api/apps/{app_id}/public/coupons/validate", json={"code": "FIXO5", "subtotal": 100})
    assert fixed.json()["discount_amount"] == 5.0

    invalid = client.post(f"/api/apps/{app_id}/public/coupons/validate", json={"code": "NAOEXISTE", "subtotal": 100})
    assert invalid.json()["valid"] is False


def test_validate_coupon_min_order_and_max_uses(client, register_user, db_session):
    app_id, headers, user_id = _published_app(client, register_user, "couponsminorder@example.com")
    _set_plan(db_session, user_id, "pro")

    client.post(
        f"/api/apps/{app_id}/coupons",
        json={"code": "MIN50", "discount_type": "fixed", "discount_value": 5, "min_order_value": 50, "max_uses": 1},
        headers=headers,
    )

    below_min = client.post(f"/api/apps/{app_id}/public/coupons/validate", json={"code": "MIN50", "subtotal": 20})
    assert below_min.json()["valid"] is False
    assert "mínimo" in below_min.json()["reason"]

    above_min = client.post(f"/api/apps/{app_id}/public/coupons/validate", json={"code": "MIN50", "subtotal": 60})
    assert above_min.json()["valid"] is True


def test_cart_checkout_applies_coupon_and_delivery_fee(client, register_user, db_session):
    app_id, headers, user_id = _published_app(client, register_user, "couponscheckout@example.com")
    _set_plan(db_session, user_id, "pro")

    item = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items",
        json={"name": "Produto", "price": 100.0},
        headers=headers,
    )
    item_id = item.json()["id"]

    client.put(
        f"/api/apps/{app_id}/module-config/calculo_frete",
        json={"settings": {"regras": "01000:15.00\n02000:20.00"}},
        headers=headers,
    )
    client.post(
        f"/api/apps/{app_id}/coupons",
        json={"code": "DESC10", "discount_type": "fixed", "discount_value": 10},
        headers=headers,
    )

    checkout = client.post(
        f"/api/apps/{app_id}/modules/catalogo/cart-checkout",
        json={
            "items": [{"item_id": item_id, "quantity": 1}],
            "customer": {"nome": "Cliente"},
            "coupon_code": "desc10",
            "fulfillment_type": "delivery",
            "cep": "01000-000",
        },
    )
    assert checkout.status_code == 201, checkout.text
    body = checkout.json()
    assert body["subtotal"] == 100.0
    assert body["delivery_fee"] == 15.0
    assert body["discount_amount"] == 10.0
    assert body["amount"] == 105.0
    assert body["coupon_code"] == "DESC10"

    coupon = db_session.query(Coupon).filter(Coupon.app_id == app_id, Coupon.code == "DESC10").first()
    assert coupon.uses_count == 1


def test_cart_checkout_rejects_below_minimum_order_value(client, register_user, db_session):
    app_id, headers, user_id = _published_app(client, register_user, "couponsminimum@example.com")
    _set_plan(db_session, user_id, "pro")

    item = client.post(
        f"/api/apps/{app_id}/modules/catalogo/items",
        json={"name": "Produto Barato", "price": 5.0},
        headers=headers,
    )
    item_id = item.json()["id"]

    client.put(
        f"/api/apps/{app_id}/module-config/pagamento_entrega",
        json={"settings": {"valor_minimo_pedido": "50"}},
        headers=headers,
    )

    checkout = client.post(
        f"/api/apps/{app_id}/modules/catalogo/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {}},
    )
    assert checkout.status_code == 400
    assert "mínimo" in checkout.json()["detail"]
