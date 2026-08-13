from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.portfolio import (
    HoldingCreate,
    HoldingResponse,
    HoldingUpdate,
)
from app.services.portfolio_service import (
    create_holding,
    delete_holding,
    get_holding,
    get_user_holdings,
    update_holding,
)


router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio"],
)


@router.get(
    "/holdings",
    response_model=list[HoldingResponse],
)
def list_holdings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_user_holdings(
        db,
        current_user.id,
    )


@router.post(
    "/holdings",
    response_model=HoldingResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_holding(
    holding_data: HoldingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_holding(
        db=db,
        user_id=current_user.id,
        symbol=holding_data.symbol,
        quantity=holding_data.quantity,
        average_buy_price=holding_data.average_buy_price,
    )


@router.put(
    "/holdings/{holding_id}",
    response_model=HoldingResponse,
)
def edit_holding(
    holding_id: int,
    holding_data: HoldingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holding = get_holding(
        db,
        holding_id,
        current_user.id,
    )

    if holding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found",
        )

    return update_holding(
        db=db,
        holding=holding,
        symbol=holding_data.symbol,
        quantity=holding_data.quantity,
        average_buy_price=holding_data.average_buy_price,
    )


@router.delete(
    "/holdings/{holding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_holding(
    holding_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holding = get_holding(
        db,
        holding_id,
        current_user.id,
    )

    if holding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found",
        )

    delete_holding(
        db,
        holding,
    )

    return None
