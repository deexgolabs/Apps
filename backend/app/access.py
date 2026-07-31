"""Controle de acesso compartilhado de app (#155) -- centraliza a checagem
"esse app é meu, ou eu sou colaborador dele" que antes era repetida (com
código idêntico) em ~14 arquivos de rota, todos só checando App.user_id ==
current_user.id. Três níveis:

- OWNER: App.user_id -- acesso total, inclusive excluir o app e gerenciar
  a equipe.
- EDITOR (colaborador): mesmo acesso de conteúdo do dono (criar/editar
  módulos, itens, pedidos, cupons, webhooks, push, etc.), mas nunca pode
  excluir o app nem mexer na equipe -- isso ficaria fácil demais de um
  editor mal-intencionado (ou só descuidado) trancar o dono fora do próprio
  app.
- VIEWER (colaborador): só leitura em tudo.

Todas as funções devolvem 404 (não 403) quando o acesso é negado, seguindo
o padrão já usado em todo o resto do código -- não confirma pra quem não
tem acesso nem que o app existe."""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import App, AppCollaborator, User

ROLE_OWNER = "owner"
ROLE_EDITOR = "editor"
ROLE_VIEWER = "viewer"

VALID_COLLABORATOR_ROLES = {ROLE_EDITOR, ROLE_VIEWER}


def get_my_role(app: App, user: User, db: Session) -> Optional[str]:
    """Devolve 'owner'/'editor'/'viewer', ou None se o usuário não tem
    nenhum acesso a esse app."""
    if app.user_id == user.id:
        return ROLE_OWNER
    collaborator = (
        db.query(AppCollaborator)
        .filter(AppCollaborator.app_id == app.id, AppCollaborator.user_id == user.id)
        .first()
    )
    return collaborator.role if collaborator else None


def get_app_for_read(app_id: int, db: Session, current_user: User) -> App:
    """Dono ou qualquer colaborador (editor ou viewer) -- usado nas rotas
    GET que só consultam dados do app."""
    app = db.query(App).filter(App.id == app_id).first()
    if not app or get_my_role(app, current_user, db) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    return app


def get_app_for_write(app_id: int, db: Session, current_user: User) -> App:
    """Dono ou colaborador editor -- usado nas rotas que criam/alteram/
    removem conteúdo do app (módulos, itens, pedidos, cupons, webhooks...).
    Viewer nunca passa aqui."""
    app = db.query(App).filter(App.id == app_id).first()
    role = get_my_role(app, current_user, db) if app else None
    if not app or role not in (ROLE_OWNER, ROLE_EDITOR):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    return app


def require_owner(app_id: int, db: Session, current_user: User) -> App:
    """Só o dono de verdade -- usado só pra excluir o app e gerenciar a
    equipe (adicionar/remover/trocar papel de colaborador)."""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    return app
