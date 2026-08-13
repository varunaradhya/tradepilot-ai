from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.valuation import PortfolioValuationResponse
from app.services.valuation_service import calculate_portfolio_valuation


router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio Valuation"],
)


@router.get(
    "/valuation",
    response_model=PortfolioValuationResponse,
)
def portfolio_valuation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return calculate_portfolio_valuation(
        db=db,
        user_id=current_user.id,
    )
