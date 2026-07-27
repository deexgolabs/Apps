from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.dependencies import get_current_end_user
from app.models import AppUser, ModuleItem, WishlistItem
from app.public_utils import get_published_app
from app.schemas import WishlistItemResponse

router = APIRouter(prefix="/api/apps/{app_id}", tags=["wishlist"])


@router.get("/wishlist/me", response_model=List[WishlistItemResponse])
async def list_my_wishlist(
    app_id: int,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    return (
        db.query(WishlistItem)
        .filter(WishlistItem.app_id == app_id, WishlistItem.end_user_id == end_user.id)
        .order_by(WishlistItem.created_at.desc())
        .all()
    )


@router.post("/modules/{module_name}/items/{item_id}/wishlist", response_model=WishlistItemResponse)
async def add_to_wishlist(
    app_id: int,
    module_name: str,
    item_id: int,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    """Idempotente — favoritar um item já favoritado apenas devolve o registro
    existente, sem criar duplicata (constraint única app_id+end_user_id+item_id)."""
    get_published_app(app_id, db)
    item = db.query(ModuleItem).filter(
        ModuleItem.id == item_id, ModuleItem.app_id == app_id, ModuleItem.module_name == module_name
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    existing = (
        db.query(WishlistItem)
        .filter(WishlistItem.app_id == app_id, WishlistItem.end_user_id == end_user.id, WishlistItem.item_id == item_id)
        .first()
    )
    if existing:
        return existing

    wishlist_item = WishlistItem(app_id=app_id, end_user_id=end_user.id, item_id=item_id)
    db.add(wishlist_item)
    db.commit()
    db.refresh(wishlist_item)
    return wishlist_item


@router.delete("/wishlist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    app_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    wishlist_item = (
        db.query(WishlistItem)
        .filter(WishlistItem.app_id == app_id, WishlistItem.end_user_id == end_user.id, WishlistItem.item_id == item_id)
        .first()
    )
    if not wishlist_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")
    db.delete(wishlist_item)
    db.commit()
