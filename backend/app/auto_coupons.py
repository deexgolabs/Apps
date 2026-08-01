import random
import string
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.jobs import enqueue_job
from app.models import AppUser, AutoCouponIssuance, AutoCouponRule, Coupon, Order

VALID_TRIGGERS = {"birthday", "first_purchase", "referral"}
BIRTHDAY_BATCH_SIZE = 50
_CODE_PREFIXES = {"birthday": "ANIV", "first_purchase": "VOLTA", "referral": "INDIQUE"}


def _generate_coupon_code(prefix: str) -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}{suffix}"


def issue_auto_coupon(db: Session, app_id: int, end_user: AppUser, trigger: str, period_key: str) -> Optional[Coupon]:
    """Gera um cupom pessoal (só o dono desse end_user pode usar) se houver
    regra ativa pro trigger, idempotente por (app, end_user, trigger,
    period_key) via AutoCouponIssuance -- nunca emite duas vezes o mesmo."""
    rule = (
        db.query(AutoCouponRule)
        .filter(AutoCouponRule.app_id == app_id, AutoCouponRule.trigger == trigger, AutoCouponRule.active == True)
        .first()
    )
    if not rule:
        return None

    already_issued = (
        db.query(AutoCouponIssuance)
        .filter(
            AutoCouponIssuance.app_id == app_id,
            AutoCouponIssuance.end_user_id == end_user.id,
            AutoCouponIssuance.trigger == trigger,
            AutoCouponIssuance.period_key == period_key,
        )
        .first()
    )
    if already_issued:
        return None

    coupon = Coupon(
        app_id=app_id,
        code=_generate_coupon_code(_CODE_PREFIXES[trigger]),
        discount_type=rule.discount_type,
        discount_value=rule.discount_value,
        end_user_id=end_user.id,
        active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=rule.valid_days),
    )
    db.add(coupon)
    db.flush()

    db.add(AutoCouponIssuance(
        app_id=app_id, end_user_id=end_user.id, trigger=trigger, period_key=period_key, coupon_id=coupon.id,
    ))
    db.commit()
    db.refresh(coupon)

    if end_user.email:
        enqueue_job(db, "email", {
            "to": end_user.email,
            "subject": "Você ganhou um cupom de desconto!",
            "html_body": (
                f"<p>Use o cupom <b>{coupon.code}</b> e ganhe desconto na sua próxima compra. "
                f"Válido até {coupon.expires_at.strftime('%d/%m/%Y')}.</p>"
            ),
        })
    return coupon


def check_and_issue_purchase_coupons(db: Session, app_id: int, order: Order) -> None:
    """Chamado quando um pedido passa a completed -- emite cupom de "primeira
    compra" se for o 1º pedido completo do cliente, e cupom de "indicação"
    pra quem indicou (só uma vez por amigo indicado)."""
    if not order.end_user_id:
        return
    end_user = db.query(AppUser).filter(AppUser.id == order.end_user_id).first()
    if not end_user:
        return

    completed_count = (
        db.query(Order)
        .filter(Order.app_id == app_id, Order.end_user_id == end_user.id, Order.status == "completed")
        .count()
    )
    if completed_count != 1:
        return

    issue_auto_coupon(db, app_id, end_user, "first_purchase", "once")

    if end_user.referred_by_id:
        referrer = db.query(AppUser).filter(AppUser.id == end_user.referred_by_id).first()
        if referrer:
            issue_auto_coupon(db, app_id, referrer, "referral", str(end_user.id))


def send_birthday_coupons(db: Session) -> None:
    """Roda no worker de background -- emite cupom de aniversário pros
    clientes cujo aniversário é hoje, uma vez por ano (idempotente)."""
    today = date.today()
    end_users = (
        db.query(AppUser)
        .filter(
            AppUser.deleted_at.is_(None),
            AppUser.birth_date.isnot(None),
            extract("month", AppUser.birth_date) == today.month,
            extract("day", AppUser.birth_date) == today.day,
        )
        .limit(BIRTHDAY_BATCH_SIZE)
        .all()
    )
    for end_user in end_users:
        issue_auto_coupon(db, end_user.app_id, end_user, "birthday", str(today.year))
