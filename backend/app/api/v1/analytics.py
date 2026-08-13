from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.analytics import PortfolioAnalytics
from app.services.analytics_service import calculate_analytics


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get(
    "/portfolio",
    response_model=PortfolioAnalytics,
)
def portfolio_analytics(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    return calculate_analytics(
        db=db,
        user_id=current_user.id,
    )
