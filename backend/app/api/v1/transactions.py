from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionListResponse, TransactionResponse, TransactionUpdate
from app.services.transaction_service import create_transaction, delete_transaction, get_transaction, get_transaction_summary, get_user_transactions, update_transaction

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def add_transaction(transaction_data: TransactionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return create_transaction(db=db, user_id=current_user.id, symbol=transaction_data.symbol, transaction_type=transaction_data.transaction_type, quantity=transaction_data.quantity, price=transaction_data.price, transaction_date=transaction_data.transaction_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=TransactionListResponse)
def list_transactions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transactions = get_user_transactions(db, current_user.id)
    return {"transactions": transactions, "summary": get_transaction_summary(db, current_user.id)}


@router.get("/{transaction_id}", response_model=TransactionResponse)
def transaction_details(transaction_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transaction = get_transaction(db, transaction_id, current_user.id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
def edit_transaction(transaction_id: int, transaction_data: TransactionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        transaction = update_transaction(db=db, transaction_id=transaction_id, user_id=current_user.id, symbol=transaction_data.symbol, transaction_type=transaction_data.transaction_type, quantity=transaction_data.quantity, price=transaction_data.price, transaction_date=transaction_data.transaction_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_transaction(transaction_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        deleted = delete_transaction(db, transaction_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if deleted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
