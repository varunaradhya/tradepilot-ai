from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.brokers.dhan import DhanAPIError, DhanClient
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.broker import (
    BrokerConnectRequest,
    BrokerConnectionResponse,
    BrokerSyncResponse,
)
from app.services.broker_service import (
    get_access_token,
    get_user_broker,
    save_broker_connection,
)
from app.services.portfolio_sync_service import (
    sync_dhan_portfolio,
)


router = APIRouter(
    prefix="/brokers",
    tags=["Brokers"],
)


@router.post(
    "/connect",
    response_model=BrokerConnectionResponse,
)
def connect_broker(
    data: BrokerConnectRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    broker_name = (
        data.broker_name
        .strip()
        .upper()
    )

    if broker_name != "DHAN":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DHAN is supported in this batch.",
        )

    client = DhanClient(
        client_id=data.client_id,
        access_token=data.access_token,
    )

    try:

        client.profile()

    except DhanAPIError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return save_broker_connection(
        db=db,
        user_id=current_user.id,
        broker_name=broker_name,
        client_id=data.client_id,
        access_token=data.access_token,
        token_expires_at=data.token_expires_at,
    )


@router.get(
    "",
    response_model=list[BrokerConnectionResponse],
)
def list_brokers(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    from app.models.broker_connection import (
        BrokerConnection,
    )

    return (
        db.query(BrokerConnection)
        .filter(
            BrokerConnection.user_id
            == current_user.id
        )
        .order_by(
            BrokerConnection.broker_name.asc()
        )
        .all()
    )


@router.post(
    "/dhan/sync",
    response_model=BrokerSyncResponse,
)
def sync_dhan(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    connection = get_user_broker(
        db,
        current_user.id,
        "DHAN",
    )

    if connection is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dhan is not connected.",
        )

    try:

        return sync_dhan_portfolio(
            db,
            connection,
        )

    except DhanAPIError as exc:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
