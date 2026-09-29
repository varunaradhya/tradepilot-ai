from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from sqlalchemy.orm import Session

from app.models.paper_ml_deployment import PaperMlDeployment
from app.models.paper_ml_model import PaperMlModel
from app.models.paper_ml_prediction import PaperMlPrediction
from app.models.paper_trade_learning import PaperTradeLearningEvent

FEATURE_NAMES = (
    "volume_ratio",
    "atr",
    "quality_score",
    "risk_reward",
    "gap_percent",
    "ema_spread_pct",
    "regime_trending_up",
    "stop_distance_pct",
    "opening_range_pct",
)
MIN_TRAINING_SAMPLES = 30
PAPER_FORWARD_SAMPLES = 30
AUTO_RETRAIN_EVERY = 10
DEFAULT_THRESHOLD = 0.60


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) else default


def learning_features(signal: dict[str, Any], entry: float | None = None) -> dict[str, float]:
    entry_price = _finite(entry if entry is not None else signal.get("entry"), 0.0)
    atr = _finite(signal.get("atr"), 0.0)
    opening_high = _finite(signal.get("opening_high"), 0.0)
    opening_low = _finite(signal.get("opening_low"), 0.0)
    opening_range_pct = ((opening_high - opening_low) / entry_price * 100.0) if entry_price > 0 else 0.0
    stop = _finite(signal.get("stop"), entry_price)
    ema_fast = _finite(signal.get("ema_fast"), 0.0)
    ema_slow = _finite(signal.get("ema_slow"), 0.0)
    ema_spread_pct = ((ema_fast - ema_slow) / entry_price * 100.0) if entry_price > 0 else 0.0
    stop_distance_pct = ((entry_price - stop) / entry_price * 100.0) if entry_price > 0 else 0.0
    regime = str(signal.get("regime", "")).upper()
    values = {
        "volume_ratio": _finite(signal.get("volume_ratio")),
        "atr": atr,
        "quality_score": _finite(signal.get("quality_score")),
        "risk_reward": _finite(signal.get("risk_reward")),
        "gap_percent": _finite(signal.get("gap_percent")),
        "ema_spread_pct": ema_spread_pct,
        "regime_trending_up": 1.0 if regime == "TRENDING_UP" else 0.0,
        "stop_distance_pct": stop_distance_pct,
        "opening_range_pct": opening_range_pct,
    }
    return {name: _finite(values.get(name)) for name in FEATURE_NAMES}


def _fingerprint(user_id: int, session: str, trade: dict[str, Any], strategy_version: str) -> str:
    raw = json.dumps(
        {
            "user_id": user_id,
            "session": session,
            "symbol": trade.get("symbol"),
            "entry": trade.get("entry"),
            "exit": trade.get("exit"),
            "quantity": trade.get("quantity"),
            "bars_held": trade.get("bars_held"),
            "reason": trade.get("reason"),
            "strategy_version": strategy_version,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def record_trade_outcome(
    db: Session,
    user_id: int,
    session: str,
    trade: dict[str, Any],
    strategy_version: str = "V1",
    model_version: str = "RULES_V1",
    commit: bool = True,
) -> PaperTradeLearningEvent:
    features = trade.get("learning_features") or {}
    normalized = {name: _finite(features.get(name)) for name in FEATURE_NAMES}
    pnl = _finite(trade.get("net_pnl", trade.get("pnl")))
    stop = _finite(trade.get("stop"))
    entry = _finite(trade.get("entry"))
    risk_per_unit = max(entry - stop, 1e-9)
    quantity = max(_finite(trade.get("quantity"), 1.0), 1.0)
    r_multiple = pnl / (risk_per_unit * quantity)
    fingerprint = _fingerprint(user_id, session, trade, strategy_version)
    existing = db.query(PaperTradeLearningEvent).filter(
        PaperTradeLearningEvent.user_id == user_id,
        PaperTradeLearningEvent.fingerprint == fingerprint,
    ).first()
    if existing:
        return existing
    raw_event_at = trade.get("entry_time") or trade.get("signal_time") or trade.get("timestamp")
    event_at = None
    if isinstance(raw_event_at, datetime):
        event_at = raw_event_at if raw_event_at.tzinfo else raw_event_at.replace(tzinfo=timezone.utc)
    elif raw_event_at:
        try:
            event_at = datetime.fromisoformat(str(raw_event_at).replace("Z", "+00:00"))
            if event_at.tzinfo is None:
                event_at = event_at.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise ValueError("trade event timestamp must be ISO-8601") from exc
    if event_at is None:
        raise ValueError("ML learning events require an entry_time/signal_time/timestamp for temporal evaluation")
    event = PaperTradeLearningEvent(
        user_id=user_id,
        symbol=str(trade.get("symbol") or "").strip().upper() or "UNKNOWN",
        session=str(session),
        event_at=event_at,
        strategy_version=strategy_version,
        model_version=model_version,
        fingerprint=fingerprint,
        features_json=json.dumps(normalized, sort_keys=True),
        label=1 if pnl > 0 else 0,
        pnl=pnl,
        r_multiple=r_multiple,
        exit_reason=str(trade.get("reason") or "UNKNOWN"),
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    event_count = db.query(PaperTradeLearningEvent).filter(
        PaperTradeLearningEvent.user_id == user_id,
        PaperTradeLearningEvent.strategy_version == strategy_version,
    ).count()
    if commit and event_count >= MIN_TRAINING_SAMPLES and event_count % AUTO_RETRAIN_EVERY == 0:
        train_model(db, user_id, strategy_version)
    return event


def _events(db: Session, user_id: int, strategy_version: str) -> list[PaperTradeLearningEvent]:
    return db.query(PaperTradeLearningEvent).filter(
        PaperTradeLearningEvent.user_id == user_id,
        PaperTradeLearningEvent.strategy_version == strategy_version,
    ).order_by(
        PaperTradeLearningEvent.event_at.asc(),
        PaperTradeLearningEvent.id.asc(),
    ).all()


def _metrics(y_true, y_prob) -> dict[str, float]:
    from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score, brier_score_loss
    predictions = [1 if p >= 0.5 else 0 for p in y_prob]
    metrics = {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "brier": float(brier_score_loss(y_true, y_prob)),
    }
    if len(set(y_true)) == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
    else:
        metrics["roc_auc"] = 0.5
    return metrics


def train_model(db: Session, user_id: int, strategy_version: str = "V1") -> dict[str, Any]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    events = _events(db, user_id, strategy_version)
    if len(events) < MIN_TRAINING_SAMPLES:
        return {
            "trained": False,
            "reason": "INSUFFICIENT_TRAINING_DATA",
            "minimum_samples": MIN_TRAINING_SAMPLES,
            "samples": len(events),
        }
    if any(event.event_at is None for event in events):
        return {
            "trained": False,
            "reason": "MISSING_FEATURE_EVENT_TIME",
            "samples": len(events),
        }
    if any(events[index].event_at > events[index + 1].event_at for index in range(len(events) - 1)):
        return {
            "trained": False,
            "reason": "NON_CHRONOLOGICAL_FEATURE_EVENTS",
            "samples": len(events),
        }
    labels = [int(event.label) for event in events]
    if len(set(labels)) < 2:
        return {"trained": False, "reason": "SINGLE_CLASS_DATA", "samples": len(events)}

    import numpy as np

    X = np.asarray(
        [[_finite(json.loads(event.features_json).get(name)) for name in FEATURE_NAMES] for event in events],
        dtype=float,
    )
    y = np.asarray(labels, dtype=int)
    n = len(events)
    train_end = max(int(n * 0.60), 20)
    validation_end = max(int(n * 0.80), train_end + 1)
    if validation_end >= n:
        validation_end = n - 1
    if train_end >= validation_end:
        return {"trained": False, "reason": "INSUFFICIENT_TIME_SPLIT", "samples": n}
    if len(set(y[:train_end])) < 2 or len(set(y[validation_end:])) < 2:
        return {"trained": False, "reason": "TIME_SPLIT_SINGLE_CLASS", "samples": n}

    scaler = StandardScaler().fit(X[:train_end])
    model = LogisticRegression(C=0.5, max_iter=500, random_state=42)
    model.fit(scaler.transform(X[:train_end]), y[:train_end])

    validation_prob = model.predict_proba(scaler.transform(X[train_end:validation_end]))[:, 1]
    test_prob = model.predict_proba(scaler.transform(X[validation_end:]))[:, 1]
    validation_metrics = _metrics(y[train_end:validation_end], validation_prob)
    test_metrics = _metrics(y[validation_end:], test_prob)
    validated = (
        test_metrics["accuracy"] >= 0.50
        and test_metrics["brier"] < 0.25
        and test_metrics["roc_auc"] >= 0.50
    )

    previous = db.query(PaperMlModel).filter(
        PaperMlModel.user_id == user_id,
        PaperMlModel.strategy_version == strategy_version,
    ).order_by(PaperMlModel.id.desc()).first()
    next_number = 1 if previous is None else int(previous.version.rsplit("_", 1)[-1]) + 1
    version = f"ML_V{next_number}"
    payload = {
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coef": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
        "classes": model.classes_.tolist(),
    }
    metrics = {
        "validation": validation_metrics,
        "test": test_metrics,
        "train_samples": train_end,
        "validation_samples": validation_end - train_end,
        "test_samples": n - validation_end,
        "temporal_split": [0.60, 0.20, 0.20],
        "validated": validated,
    }
    db.query(PaperMlModel).filter(
        PaperMlModel.user_id == user_id,
        PaperMlModel.strategy_version == strategy_version,
    ).update({"active": False})
    record = PaperMlModel(
        user_id=user_id,
        strategy_version=strategy_version,
        version=version,
        algorithm="LOGISTIC_REGRESSION",
        feature_names_json=json.dumps(FEATURE_NAMES),
        model_json=json.dumps(payload, sort_keys=True),
        metrics_json=json.dumps(metrics, sort_keys=True),
        training_samples=n,
        validated=validated,
        active=validated,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    deployment = get_deployment(db, user_id, strategy_version)
    deployment.model_id = record.id
    db.commit()
    db.refresh(deployment)
    return {
        "trained": True,
        "model_id": record.id,
        "version": version,
        "validated": validated,
        "metrics": metrics,
        "samples": n,
    }


def _active_model(db: Session, user_id: int, strategy_version: str) -> PaperMlModel | None:
    return db.query(PaperMlModel).filter(
        PaperMlModel.user_id == user_id,
        PaperMlModel.strategy_version == strategy_version,
        PaperMlModel.active.is_(True),
        PaperMlModel.validated.is_(True),
    ).order_by(PaperMlModel.id.desc()).first()


def predict(
    db: Session,
    user_id: int,
    symbol: str,
    strategy_version: str,
    features: dict[str, Any],
    *,
    persist: bool = True,
) -> dict[str, Any]:
    model = _active_model(db, user_id, strategy_version)
    if model is None:
        return {"available": False, "decision": "NO_MODEL", "probability": None}
    payload = json.loads(model.model_json)
    vector = [_finite(features.get(name)) for name in FEATURE_NAMES]
    standardized = [
        (value - mean) / scale if scale else 0.0
        for value, mean, scale in zip(vector, payload["mean"], payload["scale"])
    ]
    score = float(payload["intercept"]) + sum(weight * value for weight, value in zip(payload["coef"], standardized))
    probability = 1.0 / (1.0 + math.exp(-max(min(score, 60.0), -60.0)))
    deployment = db.query(PaperMlDeployment).filter(
        PaperMlDeployment.user_id == user_id,
        PaperMlDeployment.strategy_version == strategy_version,
    ).first()
    threshold = float(deployment.threshold) if deployment else DEFAULT_THRESHOLD
    mode = deployment.mode if deployment else "SHADOW"
    decision = "ALLOW" if probability >= threshold else "BLOCK"
    if mode == "SHADOW":
        effective_decision = "SHADOW_ALLOW" if decision == "ALLOW" else "SHADOW_BLOCK"
    elif mode == "PAPER":
        effective_decision = decision
    else:
        effective_decision = "BLOCK_LIVE_DISABLED"
    if persist:
        db.add(PaperMlPrediction(
            user_id=user_id, model_id=model.id, symbol=symbol.strip().upper(),
            strategy_version=strategy_version, probability=probability,
            decision=effective_decision, features_json=json.dumps(learning_features(features), sort_keys=True),
        ))
        db.commit()
    return {
        "available": True,
        "model_id": model.id,
        "model_version": model.version,
        "probability": round(probability, 6),
        "threshold": threshold,
        "mode": mode,
        "decision": effective_decision,
    }


def get_deployment(db: Session, user_id: int, strategy_version: str) -> PaperMlDeployment:
    deployment = db.query(PaperMlDeployment).filter(
        PaperMlDeployment.user_id == user_id,
        PaperMlDeployment.strategy_version == strategy_version,
    ).first()
    if deployment is None:
        deployment = PaperMlDeployment(
            user_id=user_id, strategy_version=strategy_version,
            mode="SHADOW", threshold=DEFAULT_THRESHOLD,
        )
        db.add(deployment)
        db.commit()
        db.refresh(deployment)
    return deployment


def set_deployment(db: Session, user_id: int, strategy_version: str, mode: str, threshold: float = DEFAULT_THRESHOLD) -> PaperMlDeployment:
    mode = mode.upper()
    if mode not in {"SHADOW", "PAPER"}:
        raise ValueError("ML mode must be SHADOW or PAPER; live mode is disabled")
    if not 0.50 <= threshold <= 0.90:
        raise ValueError("ML threshold must be between 0.50 and 0.90")
    deployment = get_deployment(db, user_id, strategy_version)
    if mode == "PAPER":
        model = _active_model(db, user_id, strategy_version)
        if model is None:
            raise ValueError("A validated active model is required for PAPER ML mode")
        forward_count = db.query(PaperTradeLearningEvent).filter(
            PaperTradeLearningEvent.user_id == user_id,
            PaperTradeLearningEvent.strategy_version == strategy_version,
            PaperTradeLearningEvent.created_at > model.created_at,
        ).count()
        if forward_count < PAPER_FORWARD_SAMPLES:
            raise ValueError(f"PAPER ML mode requires at least {PAPER_FORWARD_SAMPLES} forward learning events after model training")
    deployment.mode = mode
    deployment.threshold = threshold
    db.commit()
    db.refresh(deployment)
    return deployment


def live_readiness(db: Session, user_id: int, strategy_version: str = "V1") -> dict[str, Any]:
    model = _active_model(db, user_id, strategy_version)
    events = _events(db, user_id, strategy_version)
    deployment = get_deployment(db, user_id, strategy_version)
    checks = {
        "validated_model": bool(model and model.validated),
        "minimum_training_data": len(events) >= MIN_TRAINING_SAMPLES,
        "paper_forward_data": len(events) >= PAPER_FORWARD_SAMPLES,
        "ml_mode_is_paper_or_shadow": deployment.mode in {"PAPER", "SHADOW"},
        "live_execution_locked": True,
    }
    return {
        "mode": "SIMULATION_ONLY",
        "live_execution_enabled": False,
        "checks": checks,
        "ready": False,
        "reason": "LIVE_BROKER_EXECUTION_IS_HARD_LOCKED",
        "model": {"id": model.id, "version": model.version, "validated": model.validated} if model else None,
        "learning_events": len(events),
        "deployment": {"mode": deployment.mode, "threshold": deployment.threshold},
    }
