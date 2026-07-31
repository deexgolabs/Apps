import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session

from app.access import get_app_for_read, get_app_for_write
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, get_optional_end_user
from app.models import App, AppUser, PushSendLog, PushSubscription, User
from app.plan_limits import get_plan_limits
from app.public_utils import get_published_app
from app.schemas import PushSubscriptionCreate, PushSendRequest, PushSendLogResponse

router = APIRouter(prefix="/api/apps/{app_id}", tags=["push"])
logger = logging.getLogger("app.push")


@router.get("/public/push/vapid-public-key")
async def get_vapid_public_key(app_id: int, db: Session = Depends(get_db)):
    get_published_app(app_id, db)
    if not settings.vapid_public_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Push notifications não configuradas nesta instância")
    return {"public_key": settings.vapid_public_key}


@router.post("/public/push/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe(
    app_id: int,
    payload: PushSubscriptionCreate,
    db: Session = Depends(get_db),
    end_user: Optional[AppUser] = Depends(get_optional_end_user),
):
    app = get_published_app(app_id, db)

    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == payload.endpoint).first()
    if existing:
        existing.app_id = app.id
        existing.end_user_id = end_user.id if end_user else None
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
    else:
        db.add(PushSubscription(
            app_id=app.id,
            end_user_id=end_user.id if end_user else None,
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
        ))
    db.commit()

    return {"message": "Inscrito com sucesso"}


def send_push_now(app_id: int, end_user_id: int, title: str, body: str, db: Session) -> None:
    """Push transacional (mudança de status de pedido) pro cliente final dono
    da assinatura -- não conta no limite mensal de push do plano (isso é
    campanha, não notificação individual). Levanta exceção se alguma
    assinatura falhar por erro transitório (rede, provedor fora do ar), pro
    worker da fila de background (app/jobs.py) decidir o retry. Assinatura
    expirada (410) é limpeza normal, não falha -- não faz sentido tentar de
    novo pra um endpoint que não existe mais."""
    if not settings.vapid_private_key:
        return
    subscriptions = (
        db.query(PushSubscription)
        .filter(PushSubscription.app_id == app_id, PushSubscription.end_user_id == end_user_id)
        .all()
    )
    transient_failure = False
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_claims_email or "mailto:admin@example.com"},
            )
        except WebPushException as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 410:
                db.delete(sub)
            else:
                logger.warning("Falha ao enviar push transacional para %s: %s", sub.endpoint, exc)
                transient_failure = True
    db.commit()
    if transient_failure:
        raise RuntimeError(f"Falha transitória ao enviar push pro end_user {end_user_id} no app {app_id}")


@router.post("/push/send")
async def send_push(
    app_id: int,
    payload: PushSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_app_for_write(app_id, db, current_user)

    if not settings.vapid_private_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Push notifications não configuradas nesta instância")

    limit = get_plan_limits(current_user.plan, db)["push_sends_per_month"]
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    sent_this_month = db.query(PushSendLog).filter(
        PushSendLog.app_id == app_id, PushSendLog.sent_at >= month_start
    ).count()
    if sent_this_month >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Limite de {limit} envio(s) de push por mês atingido para o plano '{current_user.plan}'. Faça upgrade para enviar mais."
        )

    subscriptions = db.query(PushSubscription).filter(PushSubscription.app_id == app_id).all()
    sent, failed = 0, 0

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps({"title": payload.title, "body": payload.body}),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_claims_email or "mailto:admin@example.com"},
            )
            sent += 1
        except WebPushException as exc:
            failed += 1
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 410:
                db.delete(sub)
            else:
                logger.warning("Falha ao enviar push para %s: %s", sub.endpoint, exc)

    db.add(PushSendLog(app_id=app_id, title=payload.title, body=payload.body))
    db.commit()
    return {"sent": sent, "failed": failed, "total": len(subscriptions)}


@router.get("/push/history", response_model=List[PushSendLogResponse])
async def get_push_history(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_app_for_read(app_id, db, current_user)
    return (
        db.query(PushSendLog)
        .filter(PushSendLog.app_id == app_id)
        .order_by(PushSendLog.sent_at.desc())
        .limit(50)
        .all()
    )
