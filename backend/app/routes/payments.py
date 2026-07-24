from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import App, AppConfig, Module
from app.payment_gateways import checkout_mercado_pago, checkout_paypal, checkout_pagseguro

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


async def _checkout_mercado_pago(settings: dict) -> dict:
    access_token = settings.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Módulo não configurado: falta o access_token do Mercado Pago"
        )
    valor = float(settings.get("valor") or 0)
    titulo = settings.get("titulo") or "Pagamento"
    return await checkout_mercado_pago(valor, titulo, access_token)


async def _checkout_paypal(settings: dict) -> dict:
    client_id = settings.get("client_id")
    client_secret = settings.get("client_secret")
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Módulo não configurado: falta o client_id/client_secret do PayPal"
        )
    valor = settings.get("valor") or "0"
    titulo = settings.get("titulo") or "Pagamento"
    return await checkout_paypal(valor, titulo, client_id, client_secret)


async def _checkout_pagseguro(settings: dict) -> dict:
    token = settings.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Módulo não configurado: falta o token do PagSeguro"
        )
    valor = float(settings.get("valor") or 0)
    titulo = settings.get("titulo") or "Pagamento"
    return await checkout_pagseguro(valor, titulo, token)


_CHECKOUT_HANDLERS = {
    "mercado_pago": _checkout_mercado_pago,
    "paypal": _checkout_paypal,
    "pagseguro": _checkout_pagseguro,
}


@router.post("/checkout")
async def create_checkout(app_id: int, module_name: str, db: Session = Depends(get_db)):
    """Cria uma cobrança na gateway de pagamento configurada. Rota pública —
    quem paga é o cliente final do app publicado, não o dono da conta."""
    handler = _CHECKOUT_HANDLERS.get(module_name)
    if not handler:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Módulo de pagamento inválido")

    settings = _get_module_settings(app_id, module_name, db)
    return await handler(settings)
