from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.access import get_app_for_read, get_app_for_write
from app.campaigns import VALID_CHANNELS, VALID_SEGMENTS, resolve_segment_end_user_ids
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.jobs import enqueue_job
from app.models import AppUser, Campaign, PushSendLog, PushSubscription, User
from app.routes.push import check_push_monthly_limit, send_push_to_subscriptions
from app.schemas import CampaignCreate, CampaignResponse
from app.utils import log_owner_action

router = APIRouter(prefix="/api/apps/{app_id}/campaigns", tags=["campaigns"])


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_app_for_read(app_id, db, current_user)
    return (
        db.query(Campaign)
        .filter(Campaign.app_id == app_id)
        .order_by(Campaign.sent_at.desc())
        .limit(50)
        .all()
    )


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    app_id: int,
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manda uma campanha (push ou e-mail) pra um segmento de clientes finais.
    Push soma no mesmo limite mensal do broadcast manual (/push/send); e-mail
    vai um por um pra fila de background, sem limite (mesma lógica de
    qualquer outro e-mail transacional da plataforma)."""
    app = get_app_for_write(app_id, db, current_user)

    if payload.channel not in VALID_CHANNELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Canal inválido. Use um de: {', '.join(sorted(VALID_CHANNELS))}.",
        )
    if payload.segment not in VALID_SEGMENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Segmento inválido. Use um de: {', '.join(sorted(VALID_SEGMENTS))}.",
        )
    if not payload.title.strip() or not payload.body.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Título e mensagem são obrigatórios")

    end_user_ids = resolve_segment_end_user_ids(db, app_id, payload.segment)

    recipient_count = 0
    if payload.channel == "push":
        if not settings.vapid_private_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Push notifications não configuradas nesta instância")
        check_push_monthly_limit(db, app_id, current_user.plan)

        subscriptions = (
            db.query(PushSubscription)
            .filter(PushSubscription.app_id == app_id, PushSubscription.end_user_id.in_(end_user_ids))
            .all()
        ) if end_user_ids else []
        sent, _failed = send_push_to_subscriptions(subscriptions, payload.title, payload.body, db)
        db.add(PushSendLog(app_id=app_id, title=payload.title, body=payload.body))
        recipient_count = sent
    else:
        end_users = (
            db.query(AppUser)
            .filter(AppUser.id.in_(end_user_ids), AppUser.email.isnot(None))
            .all()
        ) if end_user_ids else []
        for end_user in end_users:
            enqueue_job(db, "email", {
                "to": end_user.email,
                "subject": payload.title,
                "html_body": payload.body,
            })
        recipient_count = len(end_users)

    campaign = Campaign(
        app_id=app_id,
        channel=payload.channel,
        segment=payload.segment,
        title=payload.title,
        body=payload.body,
        recipient_count=recipient_count,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    log_owner_action(
        db, app.user_id, "send_campaign", f"app:{app.id}:{app.name}",
        app_id=app.id, details=f"{payload.channel}/{payload.segment}: {recipient_count} destinatário(s)",
    )
    return campaign
