from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.access import get_app_for_read, get_app_for_write
from app.auto_coupons import VALID_TRIGGERS
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AutoCouponRule, User
from app.schemas import AutoCouponRuleResponse, AutoCouponRuleUpdate

router = APIRouter(prefix="/api/apps/{app_id}/auto-coupons", tags=["auto-coupons"])


@router.get("", response_model=List[AutoCouponRuleResponse])
async def list_auto_coupon_rules(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_app_for_read(app_id, db, current_user)
    return db.query(AutoCouponRule).filter(AutoCouponRule.app_id == app_id).all()


@router.put("/{trigger}", response_model=AutoCouponRuleResponse)
async def upsert_auto_coupon_rule(
    app_id: int,
    trigger: str,
    payload: AutoCouponRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria ou atualiza a regra de um dos 3 gatilhos (aniversário, primeira
    compra, indicação) -- um por app, upsert simples pela chave única."""
    get_app_for_write(app_id, db, current_user)

    if trigger not in VALID_TRIGGERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gatilho inválido. Use um de: {', '.join(sorted(VALID_TRIGGERS))}.",
        )
    if payload.discount_type not in ("percent", "fixed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="discount_type deve ser 'percent' ou 'fixed'")

    rule = db.query(AutoCouponRule).filter(AutoCouponRule.app_id == app_id, AutoCouponRule.trigger == trigger).first()
    if rule:
        rule.discount_type = payload.discount_type
        rule.discount_value = payload.discount_value
        rule.valid_days = payload.valid_days
        rule.active = payload.active
    else:
        rule = AutoCouponRule(app_id=app_id, trigger=trigger, **payload.model_dump())
        db.add(rule)

    db.commit()
    db.refresh(rule)
    return rule
