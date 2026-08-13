from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionSummary,
)
from app.services.transaction_service import (
    create_transaction,
    get_transaction,
    get_transaction_summary,
    get_user_transactions,
)


router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
)


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    try:

        return create_transaction(
            db=db,
            user_id=current_user.id,
            symbol=transaction_data.symbol,
            transaction_type=transaction_data.transaction_type,
            quantity=transaction_data.quantity,
            price=transaction_data.price,
            transaction_date=transaction_data.transaction_date,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=TransactionListResponse,
)
def list_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    transactions = get_user_transactions(
        db,
        current_user.id,
    )

    summary = get_transaction_summary(
        db,
        current_user.id,
    )

    return {
        "transactions": transactions,
        "summary": summary,
    }


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
)
def transaction_details(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    transaction = get_transaction(
        db,
        transaction_id,
        current_user.id,
    )

    if transaction is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return transaction
