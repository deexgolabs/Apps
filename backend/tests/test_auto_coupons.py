from datetime import date

from app.auto_coupons import send_birthday_coupons
from app.models import AppUser, AutoCouponIssuance, BackgroundJob, Coupon


def _published_app(client, register_user, email="autocoupons@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Auto Cupons", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def _end_user(client, app_id, email, referral_code=None):
    payload = {"email": email, "password": "senha12345", "full_name": "Cliente"}
    if referral_code:
        payload["referral_code"] = referral_code
    register = client.post(f"/api/apps/{app_id}/end-users/register", json=payload)
    assert register.status_code == 201, register.text
    return register.json()


def _buy_and_complete(client, app_id, owner_headers, buyer_token):
    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Bolo", "price": 20.0},
        headers=owner_headers,
    )
    item_id = item.json()["id"]
    checkout = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Comprador"}},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert checkout.status_code == 201, checkout.text
    order_id = checkout.json()["id"]
    update = client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": "completed"}, headers=owner_headers)
    assert update.status_code == 200, update.text
    return order_id


def test_upsert_and_list_auto_coupon_rules(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "rules@example.com")

    response = client.put(
        f"/api/apps/{app_id}/auto-coupons/first_purchase",
        json={"discount_type": "percent", "discount_value": 10, "valid_days": 15, "active": True},
        headers=owner_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["trigger"] == "first_purchase"

    listed = client.get(f"/api/apps/{app_id}/auto-coupons", headers=owner_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(
        f"/api/apps/{app_id}/auto-coupons/first_purchase",
        json={"discount_type": "fixed", "discount_value": 5, "valid_days": 7, "active": False},
        headers=owner_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["discount_type"] == "fixed"
    assert updated.json()["active"] is False

    still_one = client.get(f"/api/apps/{app_id}/auto-coupons", headers=owner_headers)
    assert len(still_one.json()) == 1


def test_upsert_auto_coupon_rule_rejects_invalid_trigger(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "badtrigger@example.com")

    response = client.put(
        f"/api/apps/{app_id}/auto-coupons/vip",
        json={"discount_type": "percent", "discount_value": 10},
        headers=owner_headers,
    )
    assert response.status_code == 400


def test_auto_coupons_require_access(client, register_user):
    app_id, owner_headers = _published_app(client, register_user, "accesscoupons@example.com")
    stranger = register_user(email="strangercoupons@example.com")
    stranger_headers = {"Authorization": f"Bearer {stranger['access_token']}"}

    response = client.put(
        f"/api/apps/{app_id}/auto-coupons/first_purchase",
        json={"discount_type": "percent", "discount_value": 10},
        headers=stranger_headers,
    )
    assert response.status_code == 404


def test_first_purchase_coupon_issued_once(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "firstpurchase@example.com")
    client.put(
        f"/api/apps/{app_id}/auto-coupons/first_purchase",
        json={"discount_type": "percent", "discount_value": 10, "valid_days": 15, "active": True},
        headers=owner_headers,
    )
    buyer = _end_user(client, app_id, "firstbuyer@example.com")
    buyer_token = buyer["access_token"]
    buyer_id = buyer["user"]["id"]

    _buy_and_complete(client, app_id, owner_headers, buyer_token)

    coupons = db_session.query(Coupon).filter(Coupon.app_id == app_id, Coupon.end_user_id == buyer_id).all()
    assert len(coupons) == 1
    assert coupons[0].code.startswith("VOLTA")

    jobs = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "email").all()
    assert any(j.payload.get("to") == "firstbuyer@example.com" and "cupom" in j.payload.get("subject", "").lower() for j in jobs)

    # Segunda compra completa não deve emitir outro cupom de primeira compra.
    _buy_and_complete(client, app_id, owner_headers, buyer_token)
    coupons_after = db_session.query(Coupon).filter(Coupon.app_id == app_id, Coupon.end_user_id == buyer_id).all()
    assert len(coupons_after) == 1


def test_referral_coupon_issued_to_referrer_on_first_purchase(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "referral@example.com")
    client.put(
        f"/api/apps/{app_id}/auto-coupons/referral",
        json={"discount_type": "fixed", "discount_value": 5, "valid_days": 30, "active": True},
        headers=owner_headers,
    )

    referrer = _end_user(client, app_id, "referrer@example.com")
    referrer_code = referrer["user"]["referral_code"]
    assert referrer_code

    referred = _end_user(client, app_id, "referred@example.com", referral_code=referrer_code)
    referred_token = referred["access_token"]

    _buy_and_complete(client, app_id, owner_headers, referred_token)

    referrer_coupons = db_session.query(Coupon).filter(
        Coupon.app_id == app_id, Coupon.end_user_id == referrer["user"]["id"]
    ).all()
    assert len(referrer_coupons) == 1
    assert referrer_coupons[0].code.startswith("INDIQUE")


def test_personal_coupon_cannot_be_used_by_other_end_user(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "personalcoupon@example.com")
    client.put(
        f"/api/apps/{app_id}/auto-coupons/first_purchase",
        json={"discount_type": "percent", "discount_value": 10, "valid_days": 15, "active": True},
        headers=owner_headers,
    )
    owner_of_coupon = _end_user(client, app_id, "coupon_owner@example.com")
    _buy_and_complete(client, app_id, owner_headers, owner_of_coupon["access_token"])

    coupon = db_session.query(Coupon).filter(
        Coupon.app_id == app_id, Coupon.end_user_id == owner_of_coupon["user"]["id"]
    ).first()
    assert coupon is not None

    other_user = _end_user(client, app_id, "other_shopper@example.com")
    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Torta", "price": 30.0},
        headers=owner_headers,
    )
    item_id = item.json()["id"]

    checkout = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={
            "items": [{"item_id": item_id, "quantity": 1}],
            "customer": {"nome": "Outro"},
            "coupon_code": coupon.code,
        },
        headers={"Authorization": f"Bearer {other_user['access_token']}"},
    )
    assert checkout.status_code == 400
    assert "pessoal" in checkout.json()["detail"].lower()


def test_birthday_coupon_issued_once_per_year(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "birthday@example.com")
    client.put(
        f"/api/apps/{app_id}/auto-coupons/birthday",
        json={"discount_type": "percent", "discount_value": 15, "valid_days": 10, "active": True},
        headers=owner_headers,
    )
    buyer = _end_user(client, app_id, "birthdayperson@example.com")
    buyer_id = buyer["user"]["id"]

    today = date.today()
    end_user = db_session.query(AppUser).filter(AppUser.id == buyer_id).first()
    end_user.birth_date = date(2000, today.month, today.day)
    db_session.commit()

    send_birthday_coupons(db_session)

    coupons = db_session.query(Coupon).filter(Coupon.app_id == app_id, Coupon.end_user_id == buyer_id).all()
    assert len(coupons) == 1
    assert coupons[0].code.startswith("ANIV")

    issuances = db_session.query(AutoCouponIssuance).filter(
        AutoCouponIssuance.app_id == app_id, AutoCouponIssuance.end_user_id == buyer_id, AutoCouponIssuance.trigger == "birthday"
    ).all()
    assert len(issuances) == 1

    # Rodar de novo no mesmo dia/ano não deve duplicar.
    send_birthday_coupons(db_session)
    coupons_after = db_session.query(Coupon).filter(Coupon.app_id == app_id, Coupon.end_user_id == buyer_id).all()
    assert len(coupons_after) == 1
