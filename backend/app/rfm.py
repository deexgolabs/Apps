"""Segmentação RFM básica (Recência, Frequência, Valor monetário) -- relatório
somente leitura, calculado ao vivo a partir dos pedidos completed, sem tabela
nova. Deliberadamente simples (thresholds fixos, não percentis/quartis) --
segmentação mais sofisticada fica pra uma tarefa futura se for preciso.
Só entra na lista quem tem pelo menos 1 pedido completed (sem isso, recência/
frequência/valor não fazem sentido pro cliente)."""
from typing import List, TypedDict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AppUser, Order, utcnow

VALID_TIERS = ("campeao", "em_risco", "novo", "perdido", "regular")


class RfmCustomer(TypedDict):
    end_user_id: int
    end_user_name: str
    end_user_email: str
    recency_days: int
    frequency: int
    monetary: float
    tier: str


def _assign_tier(recency_days: int, frequency: int) -> str:
    """Regras fixas e simples, nessa ordem de prioridade:
    - perdido: não compra há muito tempo (independente de quanto comprou antes)
    - novo: só uma compra, e recente
    - campeao: compra com frequência e recentemente
    - em_risco: já comprou bastante, mas sumiu (nem tão recente, nem "perdido")
    - regular: todo o resto"""
    if recency_days > 180:
        return "perdido"
    if frequency == 1 and recency_days <= 30:
        return "novo"
    if frequency >= 3 and recency_days <= 30:
        return "campeao"
    if frequency >= 2 and recency_days > 90:
        return "em_risco"
    return "regular"


def compute_rfm(db: Session, app_id: int) -> List[RfmCustomer]:
    rows = (
        db.query(
            Order.end_user_id,
            func.max(Order.created_at).label("last_order_at"),
            func.count(Order.id).label("frequency"),
            func.sum(Order.amount).label("monetary"),
        )
        .filter(Order.app_id == app_id, Order.end_user_id.isnot(None), Order.status == "completed")
        .group_by(Order.end_user_id)
        .all()
    )
    if not rows:
        return []

    end_users = {
        u.id: u
        for u in db.query(AppUser).filter(AppUser.id.in_([r.end_user_id for r in rows])).all()
    }

    now = utcnow()
    customers: List[RfmCustomer] = []
    for row in rows:
        end_user = end_users.get(row.end_user_id)
        if not end_user:
            continue
        recency_days = (now - row.last_order_at).days
        frequency = row.frequency
        monetary = float(row.monetary or 0)
        customers.append({
            "end_user_id": end_user.id,
            "end_user_name": end_user.full_name,
            "end_user_email": end_user.email,
            "recency_days": recency_days,
            "frequency": frequency,
            "monetary": monetary,
            "tier": _assign_tier(recency_days, frequency),
        })

    customers.sort(key=lambda c: c["monetary"], reverse=True)
    return customers


def tier_counts(customers: List[RfmCustomer]) -> dict:
    counts = {tier: 0 for tier in VALID_TIERS}
    for customer in customers:
        counts[customer["tier"]] += 1
    return counts
