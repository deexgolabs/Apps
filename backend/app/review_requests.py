"""Pedido de avaliação automático pós-compra -- roda no mesmo worker de
background da fila de jobs (main.py), varrendo pedidos completed há mais de
REVIEW_REQUEST_DELAY sem pedido de avaliação enviado, e enfileirando um
e-mail com link pra avaliar os itens comprados (review_requested_at controla
o envio único por pedido)."""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.jobs import enqueue_job
from app.models import App, AppUser, Order, OrderItem, utcnow

REVIEW_REQUEST_DELAY = timedelta(hours=24)
BATCH_SIZE = 20


def send_review_requests(db: Session) -> int:
    cutoff = utcnow() - REVIEW_REQUEST_DELAY
    orders = (
        db.query(Order)
        .filter(
            Order.status == "completed",
            Order.review_requested_at.is_(None),
            Order.end_user_id.isnot(None),
            Order.updated_at <= cutoff,
        )
        .limit(BATCH_SIZE)
        .all()
    )

    sent = 0
    for order in orders:
        end_user = db.query(AppUser).filter(AppUser.id == order.end_user_id).first()
        app = db.query(App).filter(App.id == order.app_id).first()
        if not end_user or not end_user.email or not app:
            order.review_requested_at = utcnow()
            db.commit()
            continue

        item_names = [
            item.name for item in db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        ]
        items_text = ", ".join(item_names) if item_names else "sua compra"
        link = f"{settings.frontend_url}/app/{app.id}"
        enqueue_job(db, "email", {
            "to": end_user.email,
            "subject": f"O que você achou da sua compra em {app.name}?",
            "html_body": (
                f"<p>Olá {end_user.full_name}, esperamos que tenha gostado de <b>{items_text}</b> "
                f"em <b>{app.name}</b>.</p>"
                f"<p>Sua avaliação ajuda outros clientes e o lojista a melhorar.</p>"
                f"<p><a href=\"{link}\">Avaliar agora</a></p>"
            ),
        })
        order.review_requested_at = utcnow()
        db.commit()
        sent += 1

    return sent
