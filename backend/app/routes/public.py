from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import AppConfig, Module, ModuleCategory, ModuleItem
from app.schemas import CategoryResponse, ItemResponse
from app.public_utils import get_published_app
from app.item_utils import attach_rating_aggregates

router = APIRouter(prefix="/api/apps/{app_id}/public", tags=["public"])


@router.get("")
async def get_public_app(app_id: int, db: Session = Depends(get_db)):
    """Dados básicos de um app publicado, para a página pública/PWA."""
    app = get_published_app(app_id, db)
    return {
        "id": app.id,
        "name": app.name,
        "config": app.config,
        "modules": app.modules,
    }


@router.get("/module-configs")
async def get_public_module_configs(app_id: int, db: Session = Depends(get_db)):
    """Configurações de todos os módulos de um app publicado."""
    app = get_published_app(app_id, db)

    rows = (
        db.query(AppConfig, Module)
        .join(Module, AppConfig.module_id == Module.id)
        .filter(AppConfig.app_id == app.id)
        .all()
    )

    return {module.name: app_config.settings for app_config, module in rows}


@router.get("/modules/{module_name}/items", response_model=List[ItemResponse])
async def list_public_items(
    app_id: int,
    module_name: str,
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    featured_only: bool = False,
    db: Session = Depends(get_db),
):
    """Itens de um módulo de lista (cardápio, catálogo, etc.) de um app publicado."""
    app = get_published_app(app_id, db)
    query = db.query(ModuleItem).filter(ModuleItem.app_id == app.id, ModuleItem.module_name == module_name)
    if q:
        query = query.filter(ModuleItem.name.ilike(f"%{q}%"))
    if category_id is not None:
        query = query.filter(ModuleItem.category_id == category_id)
    if featured_only:
        query = query.filter(ModuleItem.extra["featured"].astext == "true")
    items = query.order_by(ModuleItem.order).all()
    return attach_rating_aggregates(items, db)


@router.get("/modules/{module_name}/categories", response_model=List[CategoryResponse])
async def list_public_categories(app_id: int, module_name: str, db: Session = Depends(get_db)):
    """Categorias de um módulo de lista de um app publicado."""
    app = get_published_app(app_id, db)
    return (
        db.query(ModuleCategory)
        .filter(ModuleCategory.app_id == app.id, ModuleCategory.module_name == module_name)
        .order_by(ModuleCategory.order)
        .all()
    )
