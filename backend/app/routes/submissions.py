from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.access import get_app_for_read
from app.database import get_db
from app.models import App, FormSubmission, User
from app.schemas import SubmissionCreate, SubmissionResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/apps", tags=["submissions"])


@router.post("/{app_id}/modules/{module_name}/submissions", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    app_id: int,
    module_name: str,
    submission_data: SubmissionCreate,
    db: Session = Depends(get_db)
):
    """Recebe o envio de um formulário do app publicado. Rota pública — não exige login,
    pois quem envia é o cliente final do app, não o dono da conta."""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    submission = FormSubmission(app_id=app_id, module_name=module_name, data=submission_data.data)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/{app_id}/modules/{module_name}/submissions", response_model=List[SubmissionResponse])
async def list_submissions(
    app_id: int,
    module_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista os envios recebidos por um módulo de formulário. Só quem tem acesso ao app pode ver."""
    get_app_for_read(app_id, db, current_user)

    return (
        db.query(FormSubmission)
        .filter(FormSubmission.app_id == app_id, FormSubmission.module_name == module_name)
        .order_by(FormSubmission.created_at.desc())
        .all()
    )
