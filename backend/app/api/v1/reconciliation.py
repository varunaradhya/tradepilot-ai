from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.brokers.dhan import DhanAPIError, DhanClient
from app.brokers.registry import registry
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.holding import Holding
from app.models.user import User
from app.schemas.reconciliation import ReconciliationResponse
from app.services.broker_service import get_access_token, get_user_broker
from app.services.reconciliation_service import reconcile_holdings

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


@router.get("", response_model=ReconciliationResponse)
def get_reconciliation(
    broker: str = "dhan",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    broker_name = broker.strip().lower()
    if not broker_name:
        raise HTTPException(status_code=422, detail="Broker is required")

    connection = get_user_broker(db, current_user.id, broker_name)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{broker_name.title()} is not connected.")

    try:
        adapter_class = registry.get(broker_name)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if broker_name != "dhan":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Broker reconciliation is not available.")

    adapter = adapter_class(DhanClient(connection.client_id, get_access_token(connection)))
    try:
        broker_holdings = adapter.get_holdings()
    except DhanAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    holdings = db.query(Holding).filter(Holding.user_id == current_user.id).all()
    return reconcile_holdings(holdings, broker_holdings, broker_name)
