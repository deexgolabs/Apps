"""Recuperação de carrinho abandonado por e-mail -- roda no mesmo worker de
background da fila de jobs (main.py), varrendo carrinhos parados há mais de
ABANDON_THRESHOLD sem virar Order, e enfileirando um e-mail de lembrete uma
única vez por carrinho (reminder_sent_at controla isso)."""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.jobs import enqueue_job
from app.models import AbandonedCart, App, AppUser, utcnow

ABANDON_THRESHOLD = timedelta(hours=1)
BATCH_SIZE = 20


def send_abandoned_cart_reminders(db: Session) -> int:
    cutoff = utcnow() - ABANDON_THRESHOLD
    carts = (
        db.query(AbandonedCart)
        .filter(AbandonedCart.reminder_sent_at.is_(None), AbandonedCart.updated_at <= cutoff)
        .limit(BATCH_SIZE)
        .all()
    )

    sent = 0
    for cart in carts:
        end_user = db.query(AppUser).filter(AppUser.id == cart.end_user_id).first()
        app = db.query(App).filter(App.id == cart.app_id).first()
        if not cart.items or not end_user or not end_user.email or not app:
            # Nada a recuperar (carrinho vazio) ou dados órfãos (app/cliente
            # excluído nesse meio-tempo) -- limpa o registro sem tentar de novo.
            db.delete(cart)
            db.commit()
            continue

        items_html = "".join(
            f"<li>{item.get('quantity')}x {item.get('name')} — R$ {float(item.get('unit_price') or 0):.2f}</li>"
            for item in cart.items
        )
        link = f"{settings.frontend_url}/app/{app.id}"
        enqueue_job(db, "email", {
            "to": end_user.email,
            "subject": f"Você esqueceu itens no carrinho em {app.name}",
            "html_body": (
                f"<p>Olá {end_user.full_name}, você deixou itens no carrinho em <b>{app.name}</b>:</p>"
                f"<ul>{items_html}</ul>"
                f"<p>Subtotal: R$ {(cart.subtotal or 0):.2f}</p>"
                f"<p><a href=\"{link}\">Voltar pro carrinho</a></p>"
            ),
        })
        cart.reminder_sent_at = utcnow()
        db.commit()
        sent += 1

    return sent
