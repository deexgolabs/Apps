from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

from app.models import ItemReview, ModuleItem


def attach_rating_aggregates(items: List[ModuleItem], db: Session) -> List[ModuleItem]:
    """Anexa avg_rating/review_count (não são coluna do modelo, só atributos
    transitórios pro Pydantic ler via from_attributes) a uma lista de itens."""
    if not items:
        return items

    item_ids = [item.id for item in items]
    rows = (
        db.query(ItemReview.item_id, func.avg(ItemReview.rating), func.count(ItemReview.id))
        .filter(ItemReview.item_id.in_(item_ids))
        .group_by(ItemReview.item_id)
        .all()
    )
    stats = {item_id: (float(avg), count) for item_id, avg, count in rows}

    for item in items:
        avg, count = stats.get(item.id, (None, 0))
        item.avg_rating = avg
        item.review_count = count

    return items
