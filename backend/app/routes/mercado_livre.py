import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.access import get_app_for_write
from app.database import get_db
from app.dependencies import get_current_user
from app.models import App, AppConfig, Module, ModuleItem, User

router = APIRouter(prefix="/api/apps/{app_id}/modules/mercado_livre", tags=["mercado-livre"])

MAX_ITEMS = 100


def _get_settings(app_id: int, db: Session) -> dict:
    module = db.query(Module).filter(Module.name == "mercado_livre").first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    app_config = db.query(AppConfig).filter(
        AppConfig.app_id == app_id,
        AppConfig.module_id == module.id
    ).first()
    return app_config.settings if app_config else {}


@router.post("/sync")
async def sync_mercado_livre(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca os produtos do vendedor no Mercado Livre e sincroniza com os itens
    do módulo (upsert por extra.ml_item_id, pra rodar de novo sem duplicar)."""
    get_app_for_write(app_id, db, current_user)
    settings = _get_settings(app_id, db)

    access_token = settings.get("access_token")
    seller_id = settings.get("user_id")
    if not access_token or not seller_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Módulo não configurado: falta o access_token e o ID do vendedor do Mercado Livre",
        )

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        search_response = await client.get(
            f"https://api.mercadolibre.com/users/{seller_id}/items/search",
            headers=headers,
            params={"limit": MAX_ITEMS},
        )
        if search_response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro do Mercado Livre: {search_response.text}",
            )

        item_ids = search_response.json().get("results", [])[:MAX_ITEMS]
        if not item_ids:
            return {"synced": 0, "total": 0}

        items_response = await client.get(
            "https://api.mercadolibre.com/items",
            headers=headers,
            params={"ids": ",".join(item_ids)},
        )
        if items_response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro do Mercado Livre: {items_response.text}",
            )
        details = items_response.json()

    existing_items = (
        db.query(ModuleItem)
        .filter(ModuleItem.app_id == app_id, ModuleItem.module_name == "mercado_livre")
        .all()
    )
    existing_by_ml_id = {i.extra.get("ml_item_id"): i for i in existing_items if i.extra.get("ml_item_id")}

    synced = 0
    for entry in details:
        if entry.get("code") != 200:
            continue
        body = entry.get("body", {})
        ml_id = body.get("id")
        if not ml_id:
            continue

        name = body.get("title") or "Produto"
        price = body.get("price")
        thumbnail = body.get("thumbnail")
        permalink = body.get("permalink")

        existing = existing_by_ml_id.get(ml_id)
        if existing:
            existing.name = name
            existing.price = price
            existing.image_url = thumbnail
            existing.extra = {"ml_item_id": ml_id, "permalink": permalink}
        else:
            db.add(ModuleItem(
                app_id=app_id,
                module_name="mercado_livre",
                name=name,
                price=price,
                image_url=thumbnail,
                extra={"ml_item_id": ml_id, "permalink": permalink},
                order=synced,
            ))
        synced += 1

    db.commit()
    return {"synced": synced, "total": len(item_ids)}
