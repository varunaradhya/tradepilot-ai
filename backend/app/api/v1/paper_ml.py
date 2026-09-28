from typing import Any
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.paper_trade_learning import PaperTradeLearningEvent
from app.models.paper_ml_model import PaperMlModel
from app.services.paper_ml_service import (
    get_deployment,
    live_readiness,
    predict,
    set_deployment,
    train_model,
)

router = APIRouter(prefix="/paper-ml", tags=["Paper ML"])


class MLDeploymentRequest(BaseModel):
    strategy_version: str = Field(default="V1", pattern="^(V1|V2)$")
    mode: str = Field(default="SHADOW", pattern="^(SHADOW|PAPER)$")
    threshold: float = Field(default=0.60, ge=0.50, le=0.90)


@router.get("/status")
def ml_status(
    strategy_version: str = "V1",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    deployment = get_deployment(db, current_user.id, strategy_version)
    readiness = live_readiness(db, current_user.id, strategy_version)
    return {
        "mode": "SIMULATION_ONLY",
        "strategy_version": strategy_version,
        "deployment": {"mode": deployment.mode, "threshold": deployment.threshold, "model_id": deployment.model_id},
        "readiness": readiness,
    }


@router.post("/train")
def ml_train(
    strategy_version: str = "V1",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return {"mode": "SIMULATION_ONLY", **train_model(db, current_user.id, strategy_version)}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/deployment")
def ml_deployment(
    payload: MLDeploymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        record = set_deployment(db, current_user.id, payload.strategy_version, payload.mode, payload.threshold)
        return {
            "mode": "SIMULATION_ONLY",
            "deployment": {
                "mode": record.mode,
                "threshold": record.threshold,
                "model_id": record.model_id,
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/readiness")
def ml_readiness(
    strategy_version: str = "V1",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return live_readiness(db, current_user.id, strategy_version)


@router.post("/predict")
def ml_predict(
    symbol: str,
    strategy_version: str = "V1",
    features: dict[str, Any] | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not features:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="features are required")
    return {"mode": "SIMULATION_ONLY", **predict(db, current_user.id, symbol, strategy_version, features)}


@router.get("/evaluation")
def ml_evaluation(
    strategy_version: str = "V1",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    events = db.query(PaperTradeLearningEvent).filter(
        PaperTradeLearningEvent.user_id == current_user.id,
        PaperTradeLearningEvent.strategy_version == strategy_version,
    ).order_by(PaperTradeLearningEvent.id.asc()).all()
    models = db.query(PaperMlModel).filter(
        PaperMlModel.user_id == current_user.id,
        PaperMlModel.strategy_version == strategy_version,
    ).order_by(PaperMlModel.id.desc()).all()
    wins = sum(1 for event in events if event.label == 1)
    pnl = sum(float(event.pnl) for event in events)
    return {
        "mode": "SIMULATION_ONLY",
        "strategy_version": strategy_version,
        "sample_count": len(events),
        "win_rate_percent": round(wins / len(events) * 100, 2) if events else 0.0,
        "net_pnl": round(pnl, 2),
        "models": [
            {
                "id": model.id,
                "version": model.version,
                "validated": model.validated,
                "active": model.active,
                "training_samples": model.training_samples,
                "metrics": json.loads(model.metrics_json),
            }
            for model in models[:10]
        ],
        "note": "Evaluation evidence is descriptive. No automatic profitability verdict or live deployment is produced.",
    }
