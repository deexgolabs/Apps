from sqlalchemy.orm import Session

from app.constants import PLAN_LIMITS
from app.models import PlanConfig


def get_plan_limits(plan_name: str, db: Session) -> dict:
    """Lê os limites do plano de PlanConfig (editável pelo admin). Cai pro
    PLAN_LIMITS fixo em constants.py se a linha não existir — defesa, já que
    seed_plan_configs() popula todas na subida do backend."""
    config = db.query(PlanConfig).filter(PlanConfig.plan_name == plan_name).first()
    if not config:
        return PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"])
    return {
        "apps": config.max_apps,
        "modules": config.max_modules,
        "items": config.max_items,
        "categories": config.max_categories,
        "push_sends_per_month": config.max_push_sends_per_month,
        "coupons": config.max_coupons,
    }


def get_plan_price(plan_name: str, db: Session) -> float:
    config = db.query(PlanConfig).filter(PlanConfig.plan_name == plan_name).first()
    if config:
        return config.price
    from app.constants import PLAN_PRICES
    return PLAN_PRICES.get(plan_name, 0)
