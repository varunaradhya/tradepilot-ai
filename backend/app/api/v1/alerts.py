import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.alerts import AlertResponse
from app.services.alert_service import list_alerts, mark_all_read, mark_read

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _response(item):
    return {"id": item.id, "type": item.type, "severity": item.severity, "symbol": item.symbol, "title": item.title, "message": item.message, "is_read": item.is_read, "created_at": item.created_at, "metadata": json.loads(item.metadata_json) if item.metadata_json else None}


@router.get("", response_model=list[AlertResponse])
def alerts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_response(item) for item in list_alerts(db, current_user.id)]


@router.post("/{alert_id}/read", response_model=AlertResponse)
def read_alert(alert_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = mark_read(db, current_user.id, alert_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return _response(item)


@router.post("/read-all")
def read_all_alerts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"marked_read": mark_all_read(db, current_user.id)}
