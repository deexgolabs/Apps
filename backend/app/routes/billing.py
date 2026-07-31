from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config import settings
from app.constants import PLAN_PRICES
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, utcnow
from app.payment_gateways import checkout_mercado_pago, checkout_paypal, checkout_pagseguro
from app.plan_limits import get_plan_price
from app.schemas import BillingCheckoutRequest, BillingConfirmRequest

PLAN_RENEWAL_DAYS = 30

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/checkout")
async def create_billing_checkout(
    payload: BillingCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.plan not in PLAN_PRICES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plano inválido")

    valor = get_plan_price(payload.plan, db)
    titulo = f"Upgrade para o plano {payload.plan}"

    if payload.gateway == "mercado_pago":
        if not settings.platform_mercado_pago_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mercado Pago não configurado nesta instância")
        return await checkout_mercado_pago(valor, titulo, settings.platform_mercado_pago_token)

    if payload.gateway == "paypal":
        if not settings.platform_paypal_client_id or not settings.platform_paypal_client_secret:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PayPal não configurado nesta instância")
        return await checkout_paypal(valor, titulo, settings.platform_paypal_client_id, settings.platform_paypal_client_secret)

    if payload.gateway == "pagseguro":
        if not settings.platform_pagseguro_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PagSeguro não configurado nesta instância")
        return await checkout_pagseguro(valor, titulo, settings.platform_pagseguro_token)

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gateway inválido")


@router.post("/confirm")
async def confirm_billing(
    payload: BillingConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirma o upgrade de plano no retorno do checkout. Não há verificação
    server-to-server (webhook/assinatura) do gateway nesta fase — é apenas a
    confirmação do redirecionamento pós-pagamento.

    A assinatura é por período (PLAN_RENEWAL_DAYS): o plano pago expira e
    volta pra 'free' automaticamente (ver get_current_user em dependencies.py)
    se o dono não pagar de novo antes do vencimento — cobrança "recorrente"
    sem depender de uma API de assinatura real do gateway."""
    if payload.plan not in PLAN_PRICES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plano inválido")

    current_user.plan = payload.plan
    current_user.plan_expires_at = utcnow() + timedelta(days=PLAN_RENEWAL_DAYS)
    db.commit()

    return {
        "message": f"Plano atualizado para {payload.plan}",
        "plan": current_user.plan,
        "plan_expires_at": current_user.plan_expires_at,
    }
