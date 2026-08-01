from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.access import get_app_for_read
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.rfm import compute_rfm, tier_counts
from app.schemas import RfmSummaryResponse

router = APIRouter(prefix="/api/apps/{app_id}/rfm", tags=["rfm"])


@router.get("", response_model=RfmSummaryResponse)
async def get_rfm_summary(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Segmentação RFM básica dos clientes -- só quem tem acesso ao app pode ver."""
    get_app_for_read(app_id, db, current_user)
    customers = compute_rfm(db, app_id)
    return RfmSummaryResponse(customers=customers, tier_counts=tier_counts(customers))
