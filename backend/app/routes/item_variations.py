from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import App, ItemVariation, ModuleItem, User
from app.schemas import VariationCreate, VariationResponse, VariationUpdate
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/apps", tags=["item-variations"])

MAX_VARIATIONS_PER_ITEM = 20


def _get_owned_item(app_id: int, module_name: str, item_id: int, db: Session, current_user: User) -> ModuleItem:
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    item = db.query(ModuleItem).filter(
        ModuleItem.id == item_id, ModuleItem.app_id == app_id, ModuleItem.module_name == module_name
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.get(
    "/{app_id}/modules/{module_name}/items/{item_id}/variations",
    response_model=List[VariationResponse],
)
async def list_variations(
    app_id: int,
    module_name: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_item(app_id, module_name, item_id, db, current_user)
    return (
        db.query(ItemVariation)
        .filter(ItemVariation.item_id == item_id)
        .order_by(ItemVariation.order)
        .all()
    )


@router.post(
    "/{app_id}/modules/{module_name}/items/{item_id}/variations",
    response_model=VariationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_variation(
    app_id: int,
    module_name: str,
    item_id: int,
    variation_data: VariationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_item(app_id, module_name, item_id, db, current_user)

    current_count = db.query(ItemVariation).filter(ItemVariation.item_id == item_id).count()
    if current_count >= MAX_VARIATIONS_PER_ITEM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite de {MAX_VARIATIONS_PER_ITEM} variações por item atingido.",
        )

    variation = ItemVariation(item_id=item_id, **variation_data.model_dump())
    db.add(variation)
    db.commit()
    db.refresh(variation)
    return variation


@router.put(
    "/{app_id}/modules/{module_name}/items/{item_id}/variations/{variation_id}",
    response_model=VariationResponse,
)
async def update_variation(
    app_id: int,
    module_name: str,
    item_id: int,
    variation_id: int,
    variation_data: VariationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_item(app_id, module_name, item_id, db, current_user)
    variation = db.query(ItemVariation).filter(
        ItemVariation.id == variation_id, ItemVariation.item_id == item_id
    ).first()
    if not variation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variation not found")

    for field, value in variation_data.model_dump(exclude_unset=True).items():
        setattr(variation, field, value)

    db.commit()
    db.refresh(variation)
    return variation


@router.delete(
    "/{app_id}/modules/{module_name}/items/{item_id}/variations/{variation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_variation(
    app_id: int,
    module_name: str,
    item_id: int,
    variation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_item(app_id, module_name, item_id, db, current_user)
    variation = db.query(ItemVariation).filter(
        ItemVariation.id == variation_id, ItemVariation.item_id == item_id
    ).first()
    if not variation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variation not found")

    db.delete(variation)
    db.commit()
    return None
