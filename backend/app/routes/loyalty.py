from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.dependencies import get_current_end_user, get_current_user
from app.models import App, AppUser, LoyaltyAccount, User
from app.schemas import LoyaltyAccountResponse, LoyaltyCustomerResponse

router = APIRouter(prefix="/api/apps/{app_id}", tags=["loyalty"])


@router.get("/loyalty/me", response_model=LoyaltyAccountResponse)
async def get_my_loyalty_balance(
    app_id: int,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    """Saldo de pontos do cliente logado. Sem conta ainda = 0 pontos (não
    precisa existir linha em loyalty_accounts até o primeiro pedido concluído)."""
    account = (
        db.query(LoyaltyAccount)
        .filter(LoyaltyAccount.app_id == app_id, LoyaltyAccount.end_user_id == end_user.id)
        .first()
    )
    return LoyaltyAccountResponse(points=account.points if account else 0)


@router.get("/loyalty", response_model=List[LoyaltyCustomerResponse])
async def list_loyalty_customers(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista de clientes com pontos, ordenada do maior saldo pro menor —
    visão do dono do app."""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    rows = (
        db.query(LoyaltyAccount, AppUser)
        .join(AppUser, LoyaltyAccount.end_user_id == AppUser.id)
        .filter(LoyaltyAccount.app_id == app_id)
        .order_by(LoyaltyAccount.points.desc())
        .all()
    )
    return [
        LoyaltyCustomerResponse(
            end_user_id=end_user.id,
            end_user_name=end_user.full_name,
            end_user_email=end_user.email,
            points=account.points,
        )
        for account, end_user in rows
    ]
