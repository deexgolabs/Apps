from app.database import SessionLocal
from app.models import Module
from app.constants import SEED_MODULES


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


if __name__ == "__main__":
    seed_modules()
    print("Módulos seedados com sucesso.")
