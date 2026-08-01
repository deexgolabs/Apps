from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_end_user
from app.models import AbandonedCart, AppUser, utcnow
from app.schemas import CartTrackingRequest

router = APIRouter(prefix="/api/apps/{app_id}/modules/{module_name}", tags=["cart-tracking"])


@router.put("/cart")
async def track_cart(
    app_id: int,
    module_name: str,
    payload: CartTrackingRequest,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    """Guarda um snapshot do carrinho do cliente logado -- só serve pra
    recuperação de carrinho abandonado por e-mail (app/abandoned_cart.py).
    Carrinho vazio remove o registro, já que não sobrou nada pra recuperar."""
    cart = db.query(AbandonedCart).filter(
        AbandonedCart.app_id == app_id,
        AbandonedCart.end_user_id == end_user.id,
        AbandonedCart.module_name == module_name,
    ).first()

    if not payload.items:
        if cart:
            db.delete(cart)
            db.commit()
        return {"tracked": False}

    items_data = [i.model_dump() for i in payload.items]
    if cart:
        cart.items = items_data
        cart.subtotal = payload.subtotal
        cart.updated_at = utcnow()
        cart.reminder_sent_at = None
    else:
        cart = AbandonedCart(
            app_id=app_id,
            end_user_id=end_user.id,
            module_name=module_name,
            items=items_data,
            subtotal=payload.subtotal,
        )
        db.add(cart)
    db.commit()
    return {"tracked": True}
