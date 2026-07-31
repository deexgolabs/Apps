import logging
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import App, Order, User, WebhookSubscription
from app.routes.orders import GATEWAY_MODULES, _get_module_settings, _mark_order_confirmed, _verify_gateway_payment
from app.schemas import WebhookSubscriptionCreate, WebhookSubscriptionResponse, WebhookSubscriptionUpdate
from app.webhook_dispatch import VALID_EVENTS

router = APIRouter(prefix="/api/apps/{app_id}/webhooks", tags=["webhooks"])
logger = logging.getLogger("app.webhooks")

MAX_WEBHOOKS_PER_APP = 5


def _get_owned_app(app_id: int, db: Session, current_user: User) -> App:
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    return app


@router.get("/subscriptions", response_model=List[WebhookSubscriptionResponse])
async def list_webhook_subscriptions(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_app(app_id, db, current_user)
    return (
        db.query(WebhookSubscription)
        .filter(WebhookSubscription.app_id == app_id)
        .order_by(WebhookSubscription.created_at.desc())
        .all()
    )


@router.post("/subscriptions", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_subscription(
    app_id: int,
    payload: WebhookSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria um webhook de saída pro app -- o `secret` retornado é usado pra
    assinar (HMAC-SHA256, header X-Webhook-Signature) todo POST enviado pra
    `url`, e só é mostrado por completo aqui na criação."""
    _get_owned_app(app_id, db, current_user)

    if payload.event not in VALID_EVENTS and payload.event != "*":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Evento inválido. Use um de: {', '.join(sorted(VALID_EVENTS))}, ou '*' para todos.",
        )
    if not payload.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL inválida")

    current_count = db.query(WebhookSubscription).filter(WebhookSubscription.app_id == app_id).count()
    if current_count >= MAX_WEBHOOKS_PER_APP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite de {MAX_WEBHOOKS_PER_APP} webhook(s) por app atingido.",
        )

    subscription = WebhookSubscription(
        app_id=app_id,
        url=payload.url,
        event=payload.event,
        secret=secrets.token_hex(24),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.put("/subscriptions/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook_subscription(
    app_id: int,
    subscription_id: int,
    payload: WebhookSubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_app(app_id, db, current_user)
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == subscription_id, WebhookSubscription.app_id == app_id
    ).first()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    if payload.event is not None and payload.event not in VALID_EVENTS and payload.event != "*":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Evento inválido. Use um de: {', '.join(sorted(VALID_EVENTS))}, ou '*' para todos.",
        )
    if payload.url is not None and not payload.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL inválida")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(subscription, field, value)

    db.commit()
    db.refresh(subscription)
    return subscription


@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_subscription(
    app_id: int,
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_app(app_id, db, current_user)
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == subscription_id, WebhookSubscription.app_id == app_id
    ).first()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    db.delete(subscription)
    db.commit()
    return None


@router.post("/{gateway}")
async def payment_gateway_webhook(
    app_id: int,
    gateway: str,
    request: Request,
    order_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Recebe a notificação de mudança de status de pagamento da gateway e
    confirma o pedido automaticamente — nunca confia no que a notificação diz,
    sempre reconsulta a gateway com nossas credenciais (mesma verificação já
    usada pelo /confirm-payment manual) antes de marcar como confirmed.

    Mercado Pago e PagSeguro: a notification_url é gerada dinamicamente no
    checkout com ?order_id=<id> embutido (essas duas gateways aceitam URL de
    notificação por pedido), então aqui já sabemos exatamente qual Order
    verificar.

    PayPal: não tem notification_url dinâmica por pedido — o webhook é
    configurado uma vez no painel de developer do PayPal apontando pra esta
    mesma rota sem order_id. Nesse caso lemos o id do pedido PayPal do corpo
    do evento e localizamos o Order local pelo payment_reference.

    Sempre devolve 200 (mesmo em erro) pra gateway não entrar em loop de
    retentativa por causa de payloads inesperados — falhas reais de
    verificação continuam disponíveis pro cliente confirmar manualmente
    voltando do checkout (fluxo /confirm-payment já existente)."""
    if gateway not in GATEWAY_MODULES:
        return {"received": True}

    order = None
    if order_id is not None:
        order = (
            db.query(Order)
            .filter(Order.id == order_id, Order.app_id == app_id, Order.payment_method == gateway)
            .first()
        )
    elif gateway == "paypal":
        try:
            body = await request.json()
        except Exception:
            body = {}
        resource_id = (body.get("resource") or {}).get("id")
        if resource_id:
            order = (
                db.query(Order)
                .filter(Order.payment_reference == resource_id, Order.app_id == app_id, Order.payment_method == "paypal")
                .first()
            )

    if not order or order.status == "confirmed":
        return {"received": True}

    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        return {"received": True}

    settings = _get_module_settings(app_id, gateway, db)
    try:
        approved = await _verify_gateway_payment(gateway, settings, order.payment_reference)
    except HTTPException:
        logger.exception(
            "Falha ao verificar pagamento via webhook (app_id=%s, order_id=%s, gateway=%s)", app_id, order.id, gateway
        )
        return {"received": True}

    if approved:
        _mark_order_confirmed(order, app, db)

    return {"received": True}
