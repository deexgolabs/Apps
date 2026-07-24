import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import App, PushSubscription, User
from app.public_utils import get_published_app
from app.schemas import PushSubscriptionCreate, PushSendRequest

router = APIRouter(prefix="/api/apps/{app_id}", tags=["push"])
logger = logging.getLogger("app.push")


def _get_owned_app(app_id: int, db: Session, current_user: User) -> App:
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    return app


@router.get("/public/push/vapid-public-key")
async def get_vapid_public_key(app_id: int, db: Session = Depends(get_db)):
    get_published_app(app_id, db)
    if not settings.vapid_public_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Push notifications não configuradas nesta instância")
    return {"public_key": settings.vapid_public_key}


@router.post("/public/push/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe(app_id: int, payload: PushSubscriptionCreate, db: Session = Depends(get_db)):
    app = get_published_app(app_id, db)

    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == payload.endpoint).first()
    if existing:
        existing.app_id = app.id
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
    else:
        db.add(PushSubscription(
            app_id=app.id,
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
        ))
    db.commit()

    return {"message": "Inscrito com sucesso"}


@router.post("/push/send")
async def send_push(
    app_id: int,
    payload: PushSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_app(app_id, db, current_user)

    if not settings.vapid_private_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Push notifications não configuradas nesta instância")

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

    db.commit()
    return {"sent": sent, "failed": failed, "total": len(subscriptions)}
