from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import App, AppConfig, Module, Order
from app.payment_gateways import (
    checkout_mercado_pago,
    checkout_paypal,
    checkout_pagseguro,
    verify_mercado_pago,
    verify_paypal,
    verify_pagseguro,
)
from app.schemas import OrderResponse

router = APIRouter(prefix="/api/apps/{app_id}/modules/{module_name}", tags=["payments"])


def _get_module_settings(app_id: int, module_name: str, db: Session) -> dict:
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    module = db.query(Module).filter(Module.name == module_name).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    app_config = db.query(AppConfig).filter(
        AppConfig.app_id == app_id,
        AppConfig.module_id == module.id
    ).first()

    return app_config.settings if app_config else {}


async def _checkout_mercado_pago(settings: dict, order: Order) -> dict:
    access_token = settings.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Módulo não configurado: falta o access_token do Mercado Pago"
        )
    valor = float(settings.get("valor") or 0)
    titulo = settings.get("titulo") or "Pagamento"
    result = await checkout_mercado_pago(valor, titulo, access_token, external_reference=str(order.id))
    return result, str(order.id)


async def _checkout_paypal(settings: dict, order: Order) -> dict:
    client_id = settings.get("client_id")
    client_secret = settings.get("client_secret")
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Módulo não configurado: falta o client_id/client_secret do PayPal"
        )
    valor = settings.get("valor") or "0"
    titulo = settings.get("titulo") or "Pagamento"
    result = await checkout_paypal(valor, titulo, client_id, client_secret)
    return result, result.get("gateway_order_id")


async def _checkout_pagseguro(settings: dict, order: Order) -> dict:
    token = settings.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Módulo não configurado: falta o token do PagSeguro"
        )
    valor = float(settings.get("valor") or 0)
    titulo = settings.get("titulo") or "Pagamento"
    result = await checkout_pagseguro(valor, titulo, token)
    return result, result.get("gateway_order_id")


_CHECKOUT_HANDLERS = {
    "mercado_pago": _checkout_mercado_pago,
    "paypal": _checkout_paypal,
    "pagseguro": _checkout_pagseguro,
}

_VERIFY_HANDLERS = {
    "mercado_pago": lambda settings, ref: verify_mercado_pago(ref, settings.get("access_token")),
    "paypal": lambda settings, ref: verify_paypal(ref, settings.get("client_id"), settings.get("client_secret")),
    "pagseguro": lambda settings, ref: verify_pagseguro(ref, settings.get("token")),
}


@router.post("/checkout")
async def create_checkout(app_id: int, module_name: str, db: Session = Depends(get_db)):
    """Cria um Order (status pending) e abre uma cobrança na gateway configurada,
    vinculando os dois via payment_reference. Rota pública — quem paga é o cliente
    final do app publicado, não o dono da conta."""
    handler = _CHECKOUT_HANDLERS.get(module_name)
    if not handler:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Módulo de pagamento inválido")

    settings = _get_module_settings(app_id, module_name, db)

    order = Order(
        app_id=app_id,
        module_name=module_name,
        data={"titulo": settings.get("titulo") or "Pagamento"},
        amount=float(settings.get("valor") or 0) if settings.get("valor") else None,
        payment_method=module_name,
        status="pending",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    result, payment_reference = await handler(settings, order)
    order.payment_reference = payment_reference
    db.commit()

    return {"checkout_url": result.get("checkout_url"), "order_id": order.id}


@router.post("/orders/{order_id}/confirm", response_model=OrderResponse)
async def confirm_payment(app_id: int, module_name: str, order_id: int, db: Session = Depends(get_db)):
    """Consulta a gateway pra ver se o pagamento foi mesmo aprovado e, se sim,
    marca o Order como confirmado. Rota pública — chamada pelo cliente final depois
    de voltar do checkout."""
    verify = _VERIFY_HANDLERS.get(module_name)
    if not verify:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Módulo de pagamento inválido")

    order = db.query(Order).filter(
        Order.id == order_id, Order.app_id == app_id, Order.module_name == module_name
    ).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status != "confirmed":
        settings = _get_module_settings(app_id, module_name, db)
        approved = await verify(settings, order.payment_reference)
        if approved:
            order.status = "confirmed"
            db.commit()
            db.refresh(order)

    return order
