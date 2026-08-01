from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.access import get_app_for_read
from app.database import get_db
from app.dependencies import get_current_user
from app.models import PageView, User
from app.public_utils import get_published_app
from app.schemas import AnalyticsSummaryModule, AnalyticsSummaryResponse, PageViewCreate

router = APIRouter(prefix="/api/apps/{app_id}/analytics", tags=["analytics"])


@router.post("/pageview", status_code=status.HTTP_204_NO_CONTENT)
async def track_pageview(app_id: int, payload: PageViewCreate, db: Session = Depends(get_db)):
    """Registra uma visita anônima -- rota pública, sem PII (visitor_hash é
    gerado e guardado no cliente, nunca IP nem dado pessoal)."""
    get_published_app(app_id, db)
    db.add(PageView(app_id=app_id, module_name=payload.module_name, visitor_hash=payload.visitor_hash))
    db.commit()
    return None


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    app_id: int,
    days: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Total de visitas, visitantes únicos e módulos mais vistos -- opcionalmente
    filtrado aos últimos `days` dias. Só quem tem acesso ao app pode ver."""
    get_app_for_read(app_id, db, current_user)

    query = db.query(PageView).filter(PageView.app_id == app_id)
    if days:
        query = query.filter(PageView.created_at >= datetime.now(timezone.utc) - timedelta(days=days))

    total_views = query.count()
    unique_visitors = query.with_entities(func.count(func.distinct(PageView.visitor_hash))).scalar() or 0

    module_rows = (
        query.filter(PageView.module_name.isnot(None))
        .with_entities(PageView.module_name, func.count(PageView.id).label("views"))
        .group_by(PageView.module_name)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )
    top_modules = [AnalyticsSummaryModule(module_name=r.module_name, views=r.views) for r in module_rows]

    return AnalyticsSummaryResponse(total_views=total_views, unique_visitors=unique_visitors, top_modules=top_modules)
