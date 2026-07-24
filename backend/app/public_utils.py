from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import App


def get_published_app(app_id: int, db: Session) -> App:
    """Busca um app que esteja publicado. Usado por todas as rotas públicas
    (quem acessa é o cliente final do app, não o dono da conta)."""
    app = db.query(App).filter(App.id == app_id, App.status == "published").first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found or not published")
    return app
