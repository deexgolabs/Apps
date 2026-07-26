from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import App, AppConfig, ModuleCategory, ModuleItem, PushSendLog, User
from app.schemas import AppCreate, AppResponse, AppUpdate
from app.dependencies import get_current_user
from app.constants import APP_TEMPLATES
from app.plan_limits import get_plan_limits
from app.utils import delete_app_cascade

router = APIRouter(prefix="/api/apps", tags=["apps"])


@router.get("/", response_model=List[AppResponse])
async def list_apps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista todos os apps do usuário"""
    apps = db.query(App).filter(App.user_id == current_user.id).all()
    return apps


@router.post("/", response_model=AppResponse, status_code=status.HTTP_201_CREATED)
async def create_app(
    app_data: AppCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria novo app, respeitando o limite de apps do plano do usuário"""
    limit = get_plan_limits(current_user.plan, db)["apps"]
    if limit is not None:
        current_count = db.query(App).filter(App.user_id == current_user.id).count()
        if current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Limite de {limit} app(s) atingido para o plano '{current_user.plan}'. Faça upgrade para criar mais."
            )

    template = APP_TEMPLATES.get(app_data.template_type, {})
    module_limit = get_plan_limits(current_user.plan, db)["modules"]

    # Config enviada no wizard (cores/logo customizados) sobrescreve o padrão do
    # template, mas não substitui o dict inteiro — só as chaves informadas.
    config = {**template.get("config", {}), **(app_data.config or {})}

    db_app = App(
        user_id=current_user.id,
        name=app_data.name,
        description=app_data.description,
        template_type=app_data.template_type,
        status="draft",
        config=config,
        modules=list(template.get("modules", []))[:module_limit]
    )
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app


@router.post("/{app_id}/duplicate", response_model=AppResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_app(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Duplica um app existente (nome, cor, módulos e configuração de cada
    módulo) como rascunho novo. Não duplica dados de uso real (itens
    cadastrados, envios de formulário, usuários finais)."""
    original = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    limit = get_plan_limits(current_user.plan, db)["apps"]
    if limit is not None:
        current_count = db.query(App).filter(App.user_id == current_user.id).count()
        if current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Limite de {limit} app(s) atingido para o plano '{current_user.plan}'. Faça upgrade para criar mais."
            )

    duplicate = App(
        user_id=current_user.id,
        name=f"{original.name} (cópia)",
        description=original.description,
        template_type=original.template_type,
        status="draft",
        config=dict(original.config or {}),
        modules=list(original.modules or []),
    )
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)

    original_configs = db.query(AppConfig).filter(AppConfig.app_id == original.id).all()
    for cfg in original_configs:
        db.add(AppConfig(app_id=duplicate.id, module_id=cfg.module_id, settings=dict(cfg.settings or {})))
    db.commit()

    return duplicate


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca app específico"""
    app = db.query(App).filter(
        App.id == app_id,
        App.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )

    return app


@router.get("/{app_id}/usage")
async def get_app_usage(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Uso atual do app vs limites do plano — itens, categorias e envios de
    push no mês corrente."""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    limits = get_plan_limits(current_user.plan, db)

    items_used = db.query(ModuleItem).filter(ModuleItem.app_id == app_id).count()
    categories_used = db.query(ModuleCategory).filter(ModuleCategory.app_id == app_id).count()

    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    push_sends_used = db.query(PushSendLog).filter(
        PushSendLog.app_id == app_id, PushSendLog.sent_at >= month_start
    ).count()

    return {
        "items": {"used": items_used, "limit": limits["items"]},
        "categories": {"used": categories_used, "limit": limits["categories"]},
        "push_sends_this_month": {"used": push_sends_used, "limit": limits["push_sends_per_month"]},
    }


@router.put("/{app_id}", response_model=AppResponse)
async def update_app(
    app_id: int,
    app_data: AppUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza app"""
    app = db.query(App).filter(
        App.id == app_id,
        App.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )

    if app_data.name is not None:
        app.name = app_data.name
    if app_data.description is not None:
        app.description = app_data.description
    if app_data.config is not None:
        app.config = app_data.config
    if app_data.modules is not None:
        module_limit = get_plan_limits(current_user.plan, db)["modules"]
        if len(app_data.modules) > module_limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Limite de {module_limit} módulo(s) atingido para o plano '{current_user.plan}'. Faça upgrade para ativar mais."
            )
        app.modules = app_data.modules
    if app_data.status is not None:
        app.status = app_data.status

    db.commit()
    db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_app(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deleta app e todos os dados filhos (categorias, itens, pedidos, usuários finais etc)."""
    app = db.query(App).filter(
        App.id == app_id,
        App.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )

    delete_app_cascade(db, app_id)
    db.commit()
    return None
