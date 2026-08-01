from datetime import timedelta

from app.abandoned_cart import send_abandoned_cart_reminders
from app.models import AbandonedCart, BackgroundJob, utcnow


def _published_app_with_item(client, register_user, email="abandoned@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Carrinho Abandonado", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Bolo", "price": 20.0},
        headers=headers,
    )
    return app_id, headers, item.json()["id"]


def _end_user_headers(client, app_id, email="cliente@example.com"):
    register_end_user = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": email, "password": "senha12345", "full_name": "Cliente"},
    )
    assert register_end_user.status_code == 201
    return {"Authorization": f"Bearer {register_end_user.json()['access_token']}"}


def test_track_cart_requires_end_user_login(client, register_user):
    app_id, _, item_id = _published_app_with_item(client, register_user, "abandonedauth@example.com")

    response = client.put(
        f"/api/apps/{app_id}/modules/cardapio/cart",
        json={"items": [{"item_id": item_id, "name": "Bolo", "quantity": 1, "unit_price": 20.0}], "subtotal": 20.0},
    )
    assert response.status_code == 401


def test_track_cart_creates_and_updates_record(client, register_user, db_session):
    app_id, _, item_id = _published_app_with_item(client, register_user, "abandonedcreate@example.com")
    end_user_headers = _end_user_headers(client, app_id, "clientecreate@example.com")

    created = client.put(
        f"/api/apps/{app_id}/modules/cardapio/cart",
        json={"items": [{"item_id": item_id, "name": "Bolo", "quantity": 1, "unit_price": 20.0}], "subtotal": 20.0},
        headers=end_user_headers,
    )
    assert created.status_code == 200
    assert created.json() == {"tracked": True}

    cart = db_session.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).first()
    assert cart is not None
    assert cart.items == [{"item_id": item_id, "name": "Bolo", "quantity": 1, "unit_price": 20.0}]
    assert cart.subtotal == 20.0

    updated = client.put(
        f"/api/apps/{app_id}/modules/cardapio/cart",
        json={"items": [{"item_id": item_id, "name": "Bolo", "quantity": 3, "unit_price": 20.0}], "subtotal": 60.0},
        headers=end_user_headers,
    )
    assert updated.status_code == 200
    db_session.refresh(cart)
    assert cart.subtotal == 60.0
    assert db_session.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).count() == 1


def test_track_cart_with_empty_items_deletes_record(client, register_user, db_session):
    app_id, _, item_id = _published_app_with_item(client, register_user, "abandonedempty@example.com")
    end_user_headers = _end_user_headers(client, app_id, "clienteempty@example.com")

    client.put(
        f"/api/apps/{app_id}/modules/cardapio/cart",
        json={"items": [{"item_id": item_id, "name": "Bolo", "quantity": 1, "unit_price": 20.0}], "subtotal": 20.0},
        headers=end_user_headers,
    )
    cleared = client.put(
        f"/api/apps/{app_id}/modules/cardapio/cart",
        json={"items": [], "subtotal": 0},
        headers=end_user_headers,
    )
    assert cleared.status_code == 200
    assert cleared.json() == {"tracked": False}
    assert db_session.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).count() == 0


def test_cart_checkout_clears_abandoned_cart_tracking(client, register_user, db_session):
    app_id, _, item_id = _published_app_with_item(client, register_user, "abandonedcheckout@example.com")
    end_user_headers = _end_user_headers(client, app_id, "clientecheckout@example.com")

    client.put(
        f"/api/apps/{app_id}/modules/cardapio/cart",
        json={"items": [{"item_id": item_id, "name": "Bolo", "quantity": 1, "unit_price": 20.0}], "subtotal": 20.0},
        headers=end_user_headers,
    )
    assert db_session.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).count() == 1

    checkout = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Cliente"}},
        headers=end_user_headers,
    )
    assert checkout.status_code == 201, checkout.text
    assert db_session.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).count() == 0


def test_send_abandoned_cart_reminders_skips_recent_carts(client, register_user, db_session):
    app_id, _, item_id = _published_app_with_item(client, register_user, "abandonedrecent@example.com")
    end_user_headers = _end_user_headers(client, app_id, "clienterecent@example.com")

    client.put(
        f"/api/apps/{app_id}/modules/cardapio/cart",
        json={"items": [{"item_id": item_id, "name": "Bolo", "quantity": 1, "unit_price": 20.0}], "subtotal": 20.0},
        headers=end_user_headers,
    )

    sent = send_abandoned_cart_reminders(db_session)
    assert sent == 0
    cart = db_session.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).first()
    assert cart is not None
    assert cart.reminder_sent_at is None


def test_send_abandoned_cart_reminders_sends_once_for_old_cart(client, register_user, db_session):
    app_id, _, item_id = _published_app_with_item(client, register_user, "abandonedold@example.com")
    end_user_headers = _end_user_headers(client, app_id, "clienteold@example.com")

    client.put(
        f"/api/apps/{app_id}/modules/cardapio/cart",
        json={"items": [{"item_id": item_id, "name": "Bolo", "quantity": 2, "unit_price": 20.0}], "subtotal": 40.0},
        headers=end_user_headers,
    )
    cart = db_session.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).first()
    cart.updated_at = utcnow() - timedelta(hours=2)
    db_session.commit()

    sent = send_abandoned_cart_reminders(db_session)
    assert sent == 1

    job = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "email").order_by(BackgroundJob.id.desc()).first()
    assert job is not None
    assert job.payload["to"] == "clienteold@example.com"
    assert "Bolo" in job.payload["html_body"]

    db_session.refresh(cart)
    assert cart.reminder_sent_at is not None

    # Rodar de novo não manda um segundo e-mail pro mesmo carrinho.
    sent_again = send_abandoned_cart_reminders(db_session)
    assert sent_again == 0


def test_send_abandoned_cart_reminders_cleans_up_orphaned_cart(db_session, client, register_user):
    app_id, _, item_id = _published_app_with_item(client, register_user, "abandonedorphan@example.com")
    end_user_headers = _end_user_headers(client, app_id, "clienteorphan@example.com")

    client.put(
        f"/api/apps/{app_id}/modules/cardapio/cart",
        json={"items": [{"item_id": item_id, "name": "Bolo", "quantity": 1, "unit_price": 20.0}], "subtotal": 20.0},
        headers=end_user_headers,
    )
    cart = db_session.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).first()
    cart.items = []
    cart.updated_at = utcnow() - timedelta(hours=2)
    db_session.commit()

    sent = send_abandoned_cart_reminders(db_session)
    assert sent == 0
    assert db_session.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).count() == 0


def test_delete_account_removes_abandoned_cart(client, register_user, db_session):
    app_id, _, item_id = _published_app_with_item(client, register_user, "abandoneddelete@example.com")
    end_user_headers = _end_user_headers(client, app_id, "clientedelete@example.com")

    client.put(
        f"/api/apps/{app_id}/modules/cardapio/cart",
        json={"items": [{"item_id": item_id, "name": "Bolo", "quantity": 1, "unit_price": 20.0}], "subtotal": 20.0},
        headers=end_user_headers,
    )
    assert db_session.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).count() == 1

    deleted = client.delete(f"/api/apps/{app_id}/end-users/me", headers=end_user_headers)
    assert deleted.status_code == 200
    assert db_session.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).count() == 0
