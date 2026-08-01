from datetime import timedelta

from app.models import BackgroundJob, Order, utcnow
from app.review_requests import send_review_requests


def _published_app(client, register_user, email="reviewreq@example.com"):
    data = register_user(email=email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    create = client.post(
        "/api/apps/",
        json={"name": "App Pedido Avaliacao", "description": "", "template_type": "other"},
        headers=headers,
    )
    app_id = create.json()["id"]
    client.put(f"/api/apps/{app_id}", json={"status": "published"}, headers=headers)
    return app_id, headers


def _end_user_headers_and_token(client, app_id, email):
    register = client.post(
        f"/api/apps/{app_id}/end-users/register",
        json={"email": email, "password": "senha12345", "full_name": "Cliente"},
    )
    assert register.status_code == 201, register.text
    token = register.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, token


def _buy_and_complete(client, app_id, owner_headers, buyer_headers, item_name="Bolo"):
    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": item_name, "price": 20.0},
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
    return order_id


def test_review_request_skips_recently_completed_order(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "reviewrecent@example.com")
    buyer_headers, _ = _end_user_headers_and_token(client, app_id, "buyerrecent@example.com")
    order_id = _buy_and_complete(client, app_id, owner_headers, buyer_headers)

    sent = send_review_requests(db_session)
    assert sent == 0

    order = db_session.query(Order).filter(Order.id == order_id).first()
    assert order.review_requested_at is None


def test_review_request_sent_once_for_old_completed_order(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "reviewold@example.com")
    buyer_headers, _ = _end_user_headers_and_token(client, app_id, "buyerold@example.com")
    order_id = _buy_and_complete(client, app_id, owner_headers, buyer_headers, item_name="Torta")

    order = db_session.query(Order).filter(Order.id == order_id).first()
    order.updated_at = utcnow() - timedelta(hours=25)
    db_session.commit()

    sent = send_review_requests(db_session)
    assert sent == 1

    job = db_session.query(BackgroundJob).filter(BackgroundJob.job_type == "email").order_by(BackgroundJob.id.desc()).first()
    assert job is not None
    assert job.payload["to"] == "buyerold@example.com"
    assert "Torta" in job.payload["html_body"]

    db_session.refresh(order)
    assert order.review_requested_at is not None

    # Rodar de novo não manda um segundo pedido de avaliação pro mesmo pedido.
    sent_again = send_review_requests(db_session)
    assert sent_again == 0


def test_review_request_not_sent_for_order_without_end_user(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "reviewguest@example.com")

    order = client.post(
        f"/api/apps/{app_id}/modules/formulario_delivery/orders",
        json={"data": {"nome": "Convidado", "telefone": "11999999999"}},
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]

    client.put(f"/api/apps/{app_id}/orders/{order_id}", json={"status": "completed"}, headers=owner_headers)

    db_order = db_session.query(Order).filter(Order.id == order_id).first()
    db_order.updated_at = utcnow() - timedelta(hours=25)
    db_session.commit()

    sent = send_review_requests(db_session)
    assert sent == 0


def test_review_request_not_sent_for_non_completed_order(client, register_user, db_session):
    app_id, owner_headers = _published_app(client, register_user, "reviewpending@example.com")
    buyer_headers, _ = _end_user_headers_and_token(client, app_id, "buyerpending@example.com")

    item = client.post(
        f"/api/apps/{app_id}/modules/cardapio/items",
        json={"name": "Bolo", "price": 20.0},
        headers=owner_headers,
    )
    item_id = item.json()["id"]
    checkout = client.post(
        f"/api/apps/{app_id}/modules/cardapio/cart-checkout",
        json={"items": [{"item_id": item_id, "quantity": 1}], "customer": {"nome": "Cliente"}},
        headers=buyer_headers,
    )
    order_id = checkout.json()["id"]

    order = db_session.query(Order).filter(Order.id == order_id).first()
    order.updated_at = utcnow() - timedelta(hours=25)
    db_session.commit()

    sent = send_review_requests(db_session)
    assert sent == 0
