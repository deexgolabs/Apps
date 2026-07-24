"""Bootstrap do primeiro admin da plataforma. Uso: python -m app.make_admin email@x.com"""
import sys

from app.database import SessionLocal
from app.models import User


def make_admin(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Usuário não encontrado: {email}")
            return
        user.is_admin = True
        db.commit()
        print(f"{email} agora é admin.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m app.make_admin email@x.com")
        sys.exit(1)
    make_admin(sys.argv[1])
