from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.dependencies import get_current_end_user
from app.models import AppUser, ItemReview, ModuleItem
from app.public_utils import get_published_app
from app.schemas import ReviewCreate, ReviewResponse
from app.cache import invalidate_public_cache

router = APIRouter(prefix="/api/apps/{app_id}", tags=["reviews"])


def _get_public_item(app_id: int, module_name: str, item_id: int, db: Session) -> ModuleItem:
    get_published_app(app_id, db)
    item = db.query(ModuleItem).filter(
        ModuleItem.id == item_id, ModuleItem.app_id == app_id, ModuleItem.module_name == module_name
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


def _serialize_review(review: ItemReview, end_user_name: str) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        item_id=review.item_id,
        end_user_id=review.end_user_id,
        end_user_name=end_user_name,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


@router.get(
    "/public/modules/{module_name}/items/{item_id}/reviews",
    response_model=List[ReviewResponse],
)
async def list_public_reviews(app_id: int, module_name: str, item_id: int, db: Session = Depends(get_db)):
    """Avaliações de um item — público, sem autenticação (só a criação exige login)."""
    _get_public_item(app_id, module_name, item_id, db)
    rows = (
        db.query(ItemReview, AppUser.full_name)
        .join(AppUser, ItemReview.end_user_id == AppUser.id)
        .filter(ItemReview.item_id == item_id)
        .order_by(ItemReview.created_at.desc())
        .all()
    )
    return [_serialize_review(review, name) for review, name in rows]


@router.post(
    "/modules/{module_name}/items/{item_id}/reviews",
    response_model=ReviewResponse,
)
async def create_or_update_review(
    app_id: int,
    module_name: str,
    item_id: int,
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    """Cria a avaliação do cliente logado, ou atualiza se ele já tiver avaliado
    esse item antes (upsert por causa da constraint única item_id+end_user_id)."""
    _get_public_item(app_id, module_name, item_id, db)

    review = db.query(ItemReview).filter(
        ItemReview.item_id == item_id, ItemReview.end_user_id == end_user.id
    ).first()

    if review:
        review.rating = review_data.rating
        review.comment = review_data.comment
    else:
        review = ItemReview(
            item_id=item_id,
            end_user_id=end_user.id,
            rating=review_data.rating,
            comment=review_data.comment,
        )
        db.add(review)

    db.commit()
    db.refresh(review)
    invalidate_public_cache(app_id)
    return _serialize_review(review, end_user.full_name)
