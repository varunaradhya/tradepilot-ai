from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.strategy_paper_authorization import StrategyPaperAuthorization


def authorize_strategy(
    db: Session,
    user_id: int,
    *,
    symbol: str,
    interval: str,
    strategy_version: str,
    fingerprint: str,
    evidence: dict,
) -> StrategyPaperAuthorization:
    symbol = symbol.strip().upper()
    now = datetime.now(timezone.utc)
    record = (
        db.query(StrategyPaperAuthorization)
        .filter(
            StrategyPaperAuthorization.user_id == user_id,
            StrategyPaperAuthorization.symbol == symbol,
            StrategyPaperAuthorization.interval == interval,
            StrategyPaperAuthorization.strategy_version == strategy_version,
        )
        .first()
    )
    if record is None:
        record = StrategyPaperAuthorization(
            user_id=user_id,
            symbol=symbol,
            interval=interval,
            strategy_version=strategy_version,
            fingerprint=fingerprint,
        )
        db.add(record)
    else:
        record.fingerprint = fingerprint
        record.status = "AUTHORIZED"
        record.revoked_at = None
        record.authorized_at = now
    record.evidence_json = json.dumps(evidence, sort_keys=True, separators=(",", ":"), default=str)
    db.commit()
    db.refresh(record)
    return record


def get_active_authorization(
    db: Session,
    user_id: int,
    *,
    symbol: str,
    interval: str,
    strategy_version: str,
) -> StrategyPaperAuthorization | None:
    return (
        db.query(StrategyPaperAuthorization)
        .filter(
            StrategyPaperAuthorization.user_id == user_id,
            StrategyPaperAuthorization.symbol == symbol.strip().upper(),
            StrategyPaperAuthorization.interval == interval,
            StrategyPaperAuthorization.strategy_version == strategy_version,
            StrategyPaperAuthorization.status == "AUTHORIZED",
            StrategyPaperAuthorization.revoked_at.is_(None),
        )
        .first()
    )


def revoke_strategy(
    db: Session,
    user_id: int,
    *,
    symbol: str,
    interval: str,
    strategy_version: str,
) -> bool:
    record = get_active_authorization(
        db,
        user_id,
        symbol=symbol,
        interval=interval,
        strategy_version=strategy_version,
    )
    if record is None:
        return False
    record.status = "REVOKED"
    record.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True
