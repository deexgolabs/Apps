"""Dispara eventos pros webhooks de saída que o dono configurou pro próprio
app (#188) -- assina o corpo com HMAC-SHA256 usando o `secret` de cada
assinatura, e enfileira a entrega via app.jobs (retry automático em caso de
falha, nunca bloqueia a rota que disparou o evento)."""
import hashlib
import hmac
import json

from sqlalchemy.orm import Session

from app.jobs import enqueue_job
from app.models import WebhookSubscription

VALID_EVENTS = {"order.created", "order.status_changed"}


def _sign(secret: str, body: dict) -> str:
    payload = json.dumps(body, sort_keys=True, default=str).encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def dispatch_webhook_event(db: Session, app_id: int, event: str, data: dict) -> None:
    """Enfileira uma entrega pra cada assinatura ativa do app que escuta esse
    evento (ou '*', curinga pra todos). Nunca levanta exceção pro chamador --
    um erro aqui não deve derrubar a criação/atualização do pedido que
    disparou o evento."""
    subscriptions = (
        db.query(WebhookSubscription)
        .filter(
            WebhookSubscription.app_id == app_id,
            WebhookSubscription.active == True,  # noqa: E712
            WebhookSubscription.event.in_([event, "*"]),
        )
        .all()
    )
    for sub in subscriptions:
        body = {"event": event, "data": data}
        signature = _sign(sub.secret, body)
        enqueue_job(db, "webhook", {
            "url": sub.url,
            "body": body,
            "headers": {"X-Webhook-Signature": f"sha256={signature}"},
        })
