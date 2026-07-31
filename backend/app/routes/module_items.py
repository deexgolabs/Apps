import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.access import get_app_for_read, get_app_for_write
from app.database import get_db
from app.models import App, ModuleCategory, ModuleItem, User
from app.schemas import CategoryCreate, CategoryResponse, ImportSummaryResponse, ItemCreate, ItemUpdate, ItemResponse
from app.dependencies import get_current_user
from app.plan_limits import get_plan_limits
from app.item_utils import attach_rating_aggregates
from app.cache import invalidate_public_cache

router = APIRouter(prefix="/api/apps", tags=["module-items"])


# ===== CATEGORIES =====


@router.get("/{app_id}/modules/{module_name}/categories", response_model=List[CategoryResponse])
async def list_categories(
    app_id: int,
    module_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_app_for_read(app_id, db, current_user)
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
    get_app_for_write(app_id, db, current_user)

    limit = get_plan_limits(current_user.plan, db)["categories"]
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
    invalidate_public_cache(app_id)
    return category


@router.delete("/{app_id}/modules/{module_name}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    app_id: int,
    module_name: str,
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_app_for_write(app_id, db, current_user)
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
    invalidate_public_cache(app_id)
    return None


# ===== ITEMS =====


@router.get("/{app_id}/modules/{module_name}/items", response_model=List[ItemResponse])
async def list_items(
    app_id: int,
    module_name: str,
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    featured_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_app_for_read(app_id, db, current_user)
    query = db.query(ModuleItem).filter(ModuleItem.app_id == app_id, ModuleItem.module_name == module_name)
    if q:
        query = query.filter(ModuleItem.name.ilike(f"%{q}%"))
    if category_id is not None:
        query = query.filter(ModuleItem.category_id == category_id)
    if featured_only:
        query = query.filter(ModuleItem.extra["featured"].astext == "true")
    items = query.order_by(ModuleItem.order).all()
    return attach_rating_aggregates(items, db)


@router.post("/{app_id}/modules/{module_name}/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    app_id: int,
    module_name: str,
    item_data: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_app_for_write(app_id, db, current_user)

    limit = get_plan_limits(current_user.plan, db)["items"]
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
    invalidate_public_cache(app_id)
    return item


@router.get("/{app_id}/modules/{module_name}/items/export.csv")
async def export_items_csv(
    app_id: int,
    module_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Precisa vir registrada antes de PUT/DELETE /items/{item_id} nesse arquivo,
    senão o Starlette poderia casar 'export.csv' com o path param item_id."""
    get_app_for_read(app_id, db, current_user)
    items = (
        db.query(ModuleItem, ModuleCategory.name)
        .outerjoin(ModuleCategory, ModuleItem.category_id == ModuleCategory.id)
        .filter(ModuleItem.app_id == app_id, ModuleItem.module_name == module_name)
        .order_by(ModuleItem.order)
        .all()
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["name", "description", "price", "stock", "category", "image_url"])
    for item, category_name in items:
        writer.writerow([
            item.name,
            item.description or "",
            item.price if item.price is not None else "",
            item.stock if item.stock is not None else "",
            category_name or "",
            item.image_url or "",
        ])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=catalogo_{module_name}_app_{app_id}.csv"},
    )


@router.post("/{app_id}/modules/{module_name}/items/import.csv", response_model=ImportSummaryResponse)
async def import_items_csv(
    app_id: int,
    module_name: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Importa itens em lote via CSV (colunas: name, description, price, stock,
    category, image_url — mesmo formato do export). Categorias são criadas
    automaticamente se ainda não existirem. Para no limite de itens do plano."""
    get_app_for_write(app_id, db, current_user)

    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))

    limit = get_plan_limits(current_user.plan, db)["items"]
    current_count = db.query(ModuleItem).filter(ModuleItem.app_id == app_id).count()

    categories_by_name = {
        c.name: c
        for c in db.query(ModuleCategory).filter(
            ModuleCategory.app_id == app_id, ModuleCategory.module_name == module_name
        ).all()
    }

    created = 0
    skipped = 0
    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            skipped += 1
            continue
        if current_count + created >= limit:
            skipped += 1
            continue

        category_id = None
        category_name = (row.get("category") or "").strip()
        if category_name:
            category = categories_by_name.get(category_name)
            if not category:
                category = ModuleCategory(app_id=app_id, module_name=module_name, name=category_name, order=len(categories_by_name))
                db.add(category)
                db.flush()
                categories_by_name[category_name] = category
            category_id = category.id

        price_raw = (row.get("price") or "").strip()
        stock_raw = (row.get("stock") or "").strip()

        try:
            item = ModuleItem(
                app_id=app_id,
                module_name=module_name,
                name=name,
                description=(row.get("description") or "").strip() or None,
                price=float(price_raw) if price_raw else None,
                stock=int(float(stock_raw)) if stock_raw else None,
                image_url=(row.get("image_url") or "").strip() or None,
                category_id=category_id,
            )
        except ValueError:
            skipped += 1
            continue
        db.add(item)
        created += 1

    db.commit()
    if created:
        invalidate_public_cache(app_id)

    message = None
    if skipped:
        message = f"{skipped} linha(s) ignorada(s) (sem nome ou limite de itens do plano atingido)."
    return ImportSummaryResponse(created=created, skipped=skipped, message=message)


@router.put("/{app_id}/modules/{module_name}/items/{item_id}", response_model=ItemResponse)
async def update_item(
    app_id: int,
    module_name: str,
    item_id: int,
    item_data: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_app_for_write(app_id, db, current_user)
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
    invalidate_public_cache(app_id)
    return item


@router.delete("/{app_id}/modules/{module_name}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    app_id: int,
    module_name: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_app_for_write(app_id, db, current_user)
    item = db.query(ModuleItem).filter(
        ModuleItem.id == item_id,
        ModuleItem.app_id == app_id,
        ModuleItem.module_name == module_name
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    db.delete(item)
    db.commit()
    invalidate_public_cache(app_id)
    return None
