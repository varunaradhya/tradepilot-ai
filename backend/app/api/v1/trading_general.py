from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.trading_general import TradingGeneralResponse
from app.services.trading_general_service import calculate_trading_general

router = APIRouter(prefix="/analytics", tags=["Trading General"])

@router.get("/trading-general", response_model=TradingGeneralResponse)
def trading_general(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    return calculate_trading_general(transactions)
