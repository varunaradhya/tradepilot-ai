from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
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
    query = db.query(StrategyPaperAuthorization).filter(
        StrategyPaperAuthorization.user_id == user_id,
        StrategyPaperAuthorization.symbol == symbol,
        StrategyPaperAuthorization.interval == interval,
        StrategyPaperAuthorization.strategy_version == strategy_version,
    )
    record = query.with_for_update().first()
    if record is None:
        try:
            record = StrategyPaperAuthorization(
                user_id=user_id,
                symbol=symbol,
                interval=interval,
                strategy_version=strategy_version,
                fingerprint=fingerprint,
                status="AUTHORIZED",
                authorized_at=now,
            )
            db.add(record)
            record.evidence_json = json.dumps(evidence, sort_keys=True, separators=(",", ":"), default=str)
            db.commit()
            db.refresh(record)
            return record
        except IntegrityError:
            db.rollback()
            record = query.with_for_update().one()

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
    lock: bool = False,
) -> StrategyPaperAuthorization | None:
    query = (
        db.query(StrategyPaperAuthorization)
        .filter(
            StrategyPaperAuthorization.user_id == user_id,
            StrategyPaperAuthorization.symbol == symbol.strip().upper(),
            StrategyPaperAuthorization.interval == interval,
            StrategyPaperAuthorization.strategy_version == strategy_version,
            StrategyPaperAuthorization.status == "AUTHORIZED",
            StrategyPaperAuthorization.revoked_at.is_(None),
        )
    )
    if lock:
        query = query.with_for_update()
    return query.first()


def revoke_strategy(
    db: Session,
    user_id: int,
    *,
    symbol: str,
    interval: str,
    strategy_version: str,
) -> bool:
    record = (
        db.query(StrategyPaperAuthorization)
        .filter(
            StrategyPaperAuthorization.user_id == user_id,
            StrategyPaperAuthorization.symbol == symbol.strip().upper(),
            StrategyPaperAuthorization.interval == interval,
            StrategyPaperAuthorization.strategy_version == strategy_version,
            StrategyPaperAuthorization.status == "AUTHORIZED",
            StrategyPaperAuthorization.revoked_at.is_(None),
        )
        .with_for_update()
        .first()
    )
    if record is None:
        return False
    record.status = "REVOKED"
    record.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True
