from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models import App, OwnerAuditLog, User
from app.schemas import OwnerAuditLogResponse

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


@router.get("/", response_model=List[OwnerAuditLogResponse])
async def list_owner_audit_logs(
    app_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log de auditoria das próprias ações do dono, mais recente primeiro.
    Sem app_id, traz de todos os apps do usuário; com app_id, filtra só aquele
    app -- em ambos os casos restrito ao owner_id do usuário autenticado, então
    um app_id de outro dono simplesmente não retorna nada (sem vazar 404 que
    confirmaria a existência do app de outra conta)."""
    query = (
        db.query(OwnerAuditLog, App.name)
        .outerjoin(App, OwnerAuditLog.app_id == App.id)
        .filter(OwnerAuditLog.owner_id == current_user.id)
    )
    if app_id is not None:
        query = query.filter(OwnerAuditLog.app_id == app_id)

    rows = query.order_by(OwnerAuditLog.created_at.desc()).limit(50).all()
    return [
        OwnerAuditLogResponse(
            id=log.id,
            app_id=log.app_id,
            app_name=app_name,
            action=log.action,
            target=log.target,
            details=log.details,
            created_at=log.created_at,
        )
        for log, app_name in rows
    ]
