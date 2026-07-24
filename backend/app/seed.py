from app.database import SessionLocal
from app.models import Module, PlanConfig
from app.constants import SEED_MODULES, PLAN_LIMITS, PLAN_PRICES


def seed_modules() -> None:
    db = SessionLocal()
    try:
        valid_names = {data["name"] for data in SEED_MODULES}
        db.query(Module).filter(Module.name.notin_(valid_names)).delete(synchronize_session=False)

        for data in SEED_MODULES:
            existing = db.query(Module).filter(Module.name == data["name"]).first()
            if existing:
                continue
            db.add(Module(**data))
        db.commit()
    finally:
        db.close()


def seed_plan_configs() -> None:
    """Cria a linha de cada plano em PlanConfig a partir de PLAN_LIMITS/PLAN_PRICES,
    só na primeira vez — depois disso o admin pode editar livremente pelo painel
    sem que o seed sobrescreva."""
    db = SessionLocal()
    try:
        for plan_name, limits in PLAN_LIMITS.items():
            existing = db.query(PlanConfig).filter(PlanConfig.plan_name == plan_name).first()
            if existing:
                continue
            db.add(PlanConfig(
                plan_name=plan_name,
                price=PLAN_PRICES.get(plan_name, 0),
                max_apps=limits["apps"],
                max_modules=limits["modules"],
                max_items=limits["items"],
                max_categories=limits["categories"],
                max_push_sends_per_month=limits["push_sends_per_month"],
            ))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_modules()
    seed_plan_configs()
    print("Módulos e planos seedados com sucesso.")
