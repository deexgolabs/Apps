from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.access import VALID_COLLABORATOR_ROLES, get_app_for_read, require_owner
from app.database import get_db
from app.dependencies import get_current_user
from app.models import App, AppCollaborator, User
from app.schemas import CollaboratorInvite, CollaboratorResponse, CollaboratorUpdate
from app.utils import log_owner_action

router = APIRouter(prefix="/api/apps/{app_id}/collaborators", tags=["collaborators"])

MAX_COLLABORATORS_PER_APP = 10


def _to_response(collaborator: AppCollaborator, user: User) -> CollaboratorResponse:
    return CollaboratorResponse(
        id=collaborator.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=collaborator.role,
        created_at=collaborator.created_at,
    )


@router.get("", response_model=List[CollaboratorResponse])
async def list_collaborators(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Qualquer membro da equipe (dono, editor ou viewer) pode ver quem mais
    tem acesso ao app."""
    get_app_for_read(app_id, db, current_user)
    rows = (
        db.query(AppCollaborator, User)
        .join(User, AppCollaborator.user_id == User.id)
        .filter(AppCollaborator.app_id == app_id)
        .order_by(AppCollaborator.created_at)
        .all()
    )
    return [_to_response(collaborator, user) for collaborator, user in rows]


@router.post("", response_model=CollaboratorResponse, status_code=status.HTTP_201_CREATED)
async def invite_collaborator(
    app_id: int,
    payload: CollaboratorInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Só o dono pode convidar -- exige que a pessoa já tenha uma conta na
    plataforma (sem fluxo de convite por token/e-mail pra quem ainda não se
    cadastrou, mantém o escopo simples e testável de ponta a ponta)."""
    app = require_owner(app_id, db, current_user)

    if payload.role not in VALID_COLLABORATOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Papel inválido. Use um de: {', '.join(sorted(VALID_COLLABORATOR_ROLES))}.",
        )

    invited_user = db.query(User).filter(User.email == payload.email).first()
    if not invited_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos nenhuma conta com esse e-mail. A pessoa precisa criar uma conta na plataforma primeiro.",
        )
    if invited_user.id == app.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Você já é o dono deste app.")

    existing = db.query(AppCollaborator).filter(
        AppCollaborator.app_id == app_id, AppCollaborator.user_id == invited_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Essa pessoa já faz parte da equipe.")

    current_count = db.query(AppCollaborator).filter(AppCollaborator.app_id == app_id).count()
    if current_count >= MAX_COLLABORATORS_PER_APP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite de {MAX_COLLABORATORS_PER_APP} membro(s) de equipe por app atingido.",
        )

    collaborator = AppCollaborator(app_id=app_id, user_id=invited_user.id, role=payload.role)
    db.add(collaborator)
    db.commit()
    db.refresh(collaborator)

    log_owner_action(
        db, app.user_id, "add_collaborator", f"app:{app.id}:{app.name}",
        app_id=app.id, details=f"{invited_user.email} ({payload.role})",
    )
    return _to_response(collaborator, invited_user)


@router.put("/{collaborator_id}", response_model=CollaboratorResponse)
async def update_collaborator_role(
    app_id: int,
    collaborator_id: int,
    payload: CollaboratorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = require_owner(app_id, db, current_user)

    if payload.role not in VALID_COLLABORATOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Papel inválido. Use um de: {', '.join(sorted(VALID_COLLABORATOR_ROLES))}.",
        )

    collaborator = db.query(AppCollaborator).filter(
        AppCollaborator.id == collaborator_id, AppCollaborator.app_id == app_id
    ).first()
    if not collaborator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collaborator not found")

    collaborator.role = payload.role
    db.commit()
    db.refresh(collaborator)

    user = db.query(User).filter(User.id == collaborator.user_id).first()
    log_owner_action(
        db, app.user_id, "update_collaborator_role", f"app:{app.id}:{app.name}",
        app_id=app.id, details=f"{user.email} -> {payload.role}",
    )
    return _to_response(collaborator, user)


@router.delete("/{collaborator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_collaborator(
    app_id: int,
    collaborator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """O dono pode remover qualquer colaborador; um colaborador também pode
    remover a si mesmo (sair da equipe) sem precisar do dono."""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    collaborator = db.query(AppCollaborator).filter(
        AppCollaborator.id == collaborator_id, AppCollaborator.app_id == app_id
    ).first()
    if not collaborator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collaborator not found")

    is_owner = app.user_id == current_user.id
    is_self = collaborator.user_id == current_user.id
    if not is_owner and not is_self:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    user = db.query(User).filter(User.id == collaborator.user_id).first()
    db.delete(collaborator)
    db.commit()

    log_owner_action(
        db, app.user_id, "remove_collaborator", f"app:{app.id}:{app.name}",
        app_id=app.id, details=(user.email if user else str(collaborator.user_id)),
    )
    return None
