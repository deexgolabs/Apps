from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import App, ModuleCategory, ModuleItem, User
from app.schemas import CategoryCreate, CategoryResponse, ItemCreate, ItemUpdate, ItemResponse
from app.dependencies import get_current_user
from app.constants import PLAN_LIMITS

router = APIRouter(prefix="/api/apps", tags=["module-items"])


def _get_owned_app(app_id: int, db: Session, current_user: User) -> App:
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    return app


# ===== CATEGORIES =====


@router.get("/{app_id}/modules/{module_name}/categories", response_model=List[CategoryResponse])
async def list_categories(
    app_id: int,
    module_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _get_owned_app(app_id, db, current_user)
    return (
        db.query(ModuleCategory)
        .filter(ModuleCategory.app_id == app_id, ModuleCategory.module_name == module_name)
        .order_by(ModuleCategory.order)
        .all()
    )


@router.post("/{app_id}/modules/{module_name}/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    app_id: int,
    module_name: str,
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _get_owned_app(app_id, db, current_user)

    limit = PLAN_LIMITS.get(current_user.plan, PLAN_LIMITS["free"])["categories"]
    current_count = db.query(ModuleCategory).filter(ModuleCategory.app_id == app_id).count()
    if current_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Limite de {limit} categoria(s) atingido para o plano '{current_user.plan}'. Faça upgrade para criar mais."
        )

    category = ModuleCategory(app_id=app_id, module_name=module_name, **category_data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{app_id}/modules/{module_name}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    app_id: int,
    module_name: str,
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _get_owned_app(app_id, db, current_user)
    category = db.query(ModuleCategory).filter(
        ModuleCategory.id == category_id,
        ModuleCategory.app_id == app_id,
        ModuleCategory.module_name == module_name
    ).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    db.query(ModuleItem).filter(ModuleItem.category_id == category_id).update({"category_id": None})
    db.delete(category)
    db.commit()
    return None


# ===== ITEMS =====


@router.get("/{app_id}/modules/{module_name}/items", response_model=List[ItemResponse])
async def list_items(
    app_id: int,
    module_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _get_owned_app(app_id, db, current_user)
    return (
        db.query(ModuleItem)
        .filter(ModuleItem.app_id == app_id, ModuleItem.module_name == module_name)
        .order_by(ModuleItem.order)
        .all()
    )


@router.post("/{app_id}/modules/{module_name}/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    app_id: int,
    module_name: str,
    item_data: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _get_owned_app(app_id, db, current_user)

    limit = PLAN_LIMITS.get(current_user.plan, PLAN_LIMITS["free"])["items"]
    current_count = db.query(ModuleItem).filter(ModuleItem.app_id == app_id).count()
    if current_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Limite de {limit} item(ns) atingido para o plano '{current_user.plan}'. Faça upgrade para criar mais."
        )

    item = ModuleItem(app_id=app_id, module_name=module_name, **item_data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{app_id}/modules/{module_name}/items/{item_id}", response_model=ItemResponse)
async def update_item(
    app_id: int,
    module_name: str,
    item_id: int,
    item_data: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _get_owned_app(app_id, db, current_user)
    item = db.query(ModuleItem).filter(
        ModuleItem.id == item_id,
        ModuleItem.app_id == app_id,
        ModuleItem.module_name == module_name
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    for field, value in item_data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{app_id}/modules/{module_name}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    app_id: int,
    module_name: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _get_owned_app(app_id, db, current_user)
    item = db.query(ModuleItem).filter(
        ModuleItem.id == item_id,
        ModuleItem.app_id == app_id,
        ModuleItem.module_name == module_name
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    db.delete(item)
    db.commit()
    return None
