from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import App, AppConfig, Module, User
from app.schemas import ModuleConfigResponse, ModuleConfigUpdate
from app.dependencies import get_current_user
from app.cache import invalidate_public_cache

router = APIRouter(prefix="/api/apps", tags=["module-config"])


def _get_owned_app(app_id: int, db: Session, current_user: User) -> App:
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    return app


def _get_module(module_name: str, db: Session) -> Module:
    module = db.query(Module).filter(Module.name == module_name).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return module


@router.get("/{app_id}/module-configs")
async def get_all_module_configs(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca as configurações de todos os módulos já configurados para um app"""
    _get_owned_app(app_id, db, current_user)

    rows = (
        db.query(AppConfig, Module)
        .join(Module, AppConfig.module_id == Module.id)
        .filter(AppConfig.app_id == app_id)
        .all()
    )

    return {module.name: app_config.settings for app_config, module in rows}


@router.get("/{app_id}/module-config/{module_name}", response_model=ModuleConfigResponse)
async def get_module_config(
    app_id: int,
    module_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca as configurações de um módulo específico dentro de um app"""
    _get_owned_app(app_id, db, current_user)
    module = _get_module(module_name, db)

    app_config = db.query(AppConfig).filter(
        AppConfig.app_id == app_id,
        AppConfig.module_id == module.id
    ).first()

    return {"settings": app_config.settings if app_config else {}}


@router.put("/{app_id}/module-config/{module_name}", response_model=ModuleConfigResponse)
async def update_module_config(
    app_id: int,
    module_name: str,
    config_data: ModuleConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria ou atualiza as configurações de um módulo específico dentro de um app"""
    _get_owned_app(app_id, db, current_user)
    module = _get_module(module_name, db)

    app_config = db.query(AppConfig).filter(
        AppConfig.app_id == app_id,
        AppConfig.module_id == module.id
    ).first()

    if app_config:
        app_config.settings = config_data.settings
    else:
        app_config = AppConfig(app_id=app_id, module_id=module.id, settings=config_data.settings)
        db.add(app_config)

    db.commit()
    db.refresh(app_config)
    invalidate_public_cache(app_id)
    return {"settings": app_config.settings}
