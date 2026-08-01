"""Resolução de segmento de clientes pra campanha (push/e-mail) -- ver
routes/campaigns.py. Segmentação básica por histórico de pedidos; RFM mais
sofisticado é escopo de uma tarefa futura separada (#164), não desta."""
from typing import Set

from sqlalchemy.orm import Session

from app.models import AppUser, Order

VALID_SEGMENTS = {"all", "customers", "non_customers"}
VALID_CHANNELS = {"push", "email"}


def resolve_segment_end_user_ids(db: Session, app_id: int, segment: str) -> Set[int]:
    all_ids = {
        row.id
        for row in db.query(AppUser.id).filter(AppUser.app_id == app_id, AppUser.deleted_at.is_(None)).all()
    }
    if segment == "all":
        return all_ids

    customer_ids = {
        row[0]
        for row in db.query(Order.end_user_id)
        .filter(Order.app_id == app_id, Order.end_user_id.isnot(None), Order.status == "completed")
        .distinct()
        .all()
    }
    if segment == "customers":
        return all_ids & customer_ids
    if segment == "non_customers":
        return all_ids - customer_ids

    raise ValueError(f"Segmento desconhecido: {segment}")
