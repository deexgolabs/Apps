import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import App, Order
from app.routes.orders import GATEWAY_MODULES, _get_module_settings, _mark_order_confirmed, _verify_gateway_payment

router = APIRouter(prefix="/api/apps/{app_id}/webhooks", tags=["webhooks"])
logger = logging.getLogger("app.webhooks")


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
