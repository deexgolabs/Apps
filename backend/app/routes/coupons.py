from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import App, Coupon, User
from app.schemas import (
    CouponCreate,
    CouponResponse,
    CouponUpdate,
    CouponValidateRequest,
    CouponValidateResponse,
)
from app.dependencies import get_current_user
from app.plan_limits import get_plan_limits
from app.public_utils import get_published_app

router = APIRouter(prefix="/api/apps/{app_id}", tags=["coupons"])


def _get_owned_app(app_id: int, db: Session, current_user: User) -> App:
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    return app


@router.get("/coupons", response_model=List[CouponResponse])
async def list_coupons(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_app(app_id, db, current_user)
    return db.query(Coupon).filter(Coupon.app_id == app_id).order_by(Coupon.created_at.desc()).all()


@router.post("/coupons", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    app_id: int,
    coupon_data: CouponCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_app(app_id, db, current_user)

    limit = get_plan_limits(current_user.plan, db)["coupons"]
    current_count = db.query(Coupon).filter(Coupon.app_id == app_id, Coupon.active == True).count()
    if current_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Limite de {limit} cupom(ns) atingido para o plano '{current_user.plan}'. Faça upgrade para criar mais.",
        )

    code = coupon_data.code.strip().upper()
    existing = db.query(Coupon).filter(Coupon.app_id == app_id, Coupon.code == code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um cupom com esse código.")

    coupon = Coupon(app_id=app_id, **{**coupon_data.model_dump(), "code": code})
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.put("/coupons/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    app_id: int,
    coupon_id: int,
    coupon_data: CouponUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_app(app_id, db, current_user)
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id, Coupon.app_id == app_id).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")

    for field, value in coupon_data.model_dump(exclude_unset=True).items():
        setattr(coupon, field, value)

    db.commit()
    db.refresh(coupon)
    return coupon


@router.delete("/coupons/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coupon(
    app_id: int,
    coupon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_app(app_id, db, current_user)
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id, Coupon.app_id == app_id).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")

    db.delete(coupon)
    db.commit()
    return None


def validate_coupon(app_id: int, code: str, subtotal: float, db: Session) -> tuple:
    """Retorna (coupon | None, discount_amount, reason | None) — reaproveitado
    pelo checkout de carrinho e pelo endpoint público de validação."""
    coupon = db.query(Coupon).filter(Coupon.app_id == app_id, Coupon.code == code.strip().upper()).first()
    if not coupon:
        return None, 0.0, "Cupom não encontrado"
    if not coupon.active:
        return None, 0.0, "Cupom inativo"
    if coupon.expires_at and coupon.expires_at < datetime.now(timezone.utc):
        return None, 0.0, "Cupom expirado"
    if coupon.max_uses is not None and coupon.uses_count >= coupon.max_uses:
        return None, 0.0, "Cupom esgotado"
    if coupon.min_order_value is not None and subtotal < coupon.min_order_value:
        return None, 0.0, f"Pedido mínimo de R$ {coupon.min_order_value:.2f} para esse cupom"

    if coupon.discount_type == "percent":
        discount = subtotal * (coupon.discount_value / 100)
    else:
        discount = coupon.discount_value
    discount = min(discount, subtotal)
    return coupon, discount, None


@router.post("/public/coupons/validate", response_model=CouponValidateResponse)
async def validate_coupon_public(app_id: int, payload: CouponValidateRequest, db: Session = Depends(get_db)):
    get_published_app(app_id, db)
    coupon, discount, reason = validate_coupon(app_id, payload.code, payload.subtotal, db)
    if not coupon:
        return CouponValidateResponse(valid=False, reason=reason)
    return CouponValidateResponse(valid=True, discount_amount=discount)
