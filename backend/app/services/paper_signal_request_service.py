from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.paper_signal_request import PaperSignalRequest
from app.models.paper_trade import PaperTrade


def request_fingerprint(signal: dict[str, Any]) -> str:
    canonical = {
        "session": str(signal.get("session", "")),
        "symbol": str(signal.get("symbol", "")).strip().upper(),
        "interval": str(signal.get("interval", "5")),
        "strategy_version": str(signal.get("strategy_version", "V1")),
        "action": str(signal.get("action", signal.get("direction", ""))).upper(),
        "decision": str(signal.get("decision", "")).upper(),
        "entry": signal.get("entry"),
        "stop": signal.get("stop"),
        "target": signal.get("target"),
        "lot_size": signal.get("lot_size", 1),
        "quantity": signal.get("quantity"),
        "security_id": str((signal.get("contract") or {}).get("security_id", signal.get("security_id", ""))),
        "exchange_segment": str((signal.get("contract") or {}).get("exchange_segment", signal.get("exchange_segment", ""))).upper(),
        "strike": (signal.get("contract") or {}).get("strike", signal.get("strike")),
        "option_type": str((signal.get("contract") or {}).get("option_type", signal.get("option_type", ""))).upper(),
        "expiry": (signal.get("underlying") or {}).get("expiry", signal.get("expiry")),
        "candle_timestamp": signal.get("candle_timestamp", signal.get("bar_timestamp")),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def get_request(db: Session, user_id: int, request_id: str) -> PaperSignalRequest | None:
    return (
        db.query(PaperSignalRequest)
        .filter(
            PaperSignalRequest.user_id == user_id,
            PaperSignalRequest.request_id == request_id,
        )
        .first()
    )


def claim_request(
    db: Session,
    user_id: int,
    request_id: str,
    signal: dict[str, Any],
) -> tuple[PaperSignalRequest, bool]:
    existing = get_request(db, user_id, request_id)
    if existing is not None:
        if existing.request_fingerprint != request_fingerprint(signal):
            raise ValueError("paper signal request_id was already used for a different signal")
        return existing, False

    record = PaperSignalRequest(
        user_id=user_id,
        request_id=request_id,
        symbol=str(signal["symbol"]).strip().upper(),
        strategy_version=str(signal.get("strategy_version", "V1")),
        interval=str(signal.get("interval", "5")),
        session=str(signal["session"]),
        decision="PENDING",
        request_fingerprint=request_fingerprint(signal),
        response_json="{}",
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_request(db, user_id, request_id)
        if existing is None:
            raise
        if existing.request_fingerprint != request_fingerprint(signal):
            raise ValueError("paper signal request_id was already used for a different signal")
        return existing, False
    db.refresh(record)
    return record, True


def complete_request(db: Session, record: PaperSignalRequest, response: dict[str, Any]) -> PaperSignalRequest:
    record.decision = "ACCEPTED" if response.get("accepted") else "REJECTED"
    record.response_json = json.dumps(response, sort_keys=True, separators=(",", ":"), default=str)
    db.commit()
    db.refresh(record)
    return record


def replay_response(record: PaperSignalRequest) -> dict[str, Any] | None:
    if record.decision == "PENDING":
        return None
    return json.loads(record.response_json)


def pending_request_age_seconds(record: PaperSignalRequest, now: datetime | None = None) -> float:
    """Return age of a PENDING request using UTC-safe timestamp handling."""
    if record.decision != "PENDING":
        return 0.0
    current = now or datetime.now(timezone.utc)
    created = record.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max(0.0, (current - created.astimezone(timezone.utc)).total_seconds())


def is_stale_pending_request(
    record: PaperSignalRequest,
    *,
    max_age_seconds: float = 300.0,
    now: datetime | None = None,
) -> bool:
    """Identify crash-left PENDING requests without silently retrying them."""
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    return record.decision == "PENDING" and pending_request_age_seconds(record, now) > max_age_seconds


def reconcile_pending_request(
    db: Session,
    record: PaperSignalRequest,
    signal: dict[str, Any],
) -> dict[str, Any] | None:
    """Recover a crash-left PENDING request only when its exact paper trade exists.

    This never creates or retries a trade. It only converts a durable PENDING
    request into a completed replay when exactly one matching open option trade
    can be proven to belong to the request.
    """
    if record.decision != "PENDING":
        return replay_response(record)

    contract = signal.get("contract") or {}
    security_id = str(contract.get("security_id", signal.get("security_id", ""))).strip()
    symbol = str(signal.get("symbol", "")).strip().upper()
    quantity = int(signal.get("quantity") or 0)
    entry = float(signal.get("entry") or 0)
    stop = float(signal.get("stop") or 0)
    target = float(signal.get("target") or 0)
    strategy_version = str(signal.get("strategy_version", "V1"))
    underlying = str((signal.get("underlying") or {}).get("symbol", signal.get("underlying_symbol", symbol))).strip().upper()
    expiry = (signal.get("underlying") or {}).get("expiry", signal.get("expiry"))
    strike = contract.get("strike", signal.get("strike"))
    option_type = str(contract.get("option_type", signal.get("option_type", ""))).strip().upper()
    if not security_id or quantity <= 0 or entry <= 0 or stop <= 0 or target <= 0:
        return None

    candidates = (
        db.query(PaperTrade)
        .filter(
            PaperTrade.user_id == record.user_id,
            PaperTrade.status == "OPEN",
            PaperTrade.asset_type == "OPTION",
            PaperTrade.security_id == security_id,
            PaperTrade.quantity == quantity,
            PaperTrade.strategy_version == strategy_version,
        )
        .all()
    )
    matches = []
    for trade in candidates:
        try:
            created = trade.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            request_created = record.created_at
            if request_created.tzinfo is None:
                request_created = request_created.replace(tzinfo=timezone.utc)
            if created.astimezone(timezone.utc) < request_created.astimezone(timezone.utc):
                continue
            if trade.symbol.upper() != symbol:
                continue
            if abs(float(trade.entry_price) - entry) > 1e-9:
                continue
            if abs(float(trade.stop_price) - stop) > 1e-9 or abs(float(trade.target_price) - target) > 1e-9:
                continue
            if str(trade.underlying or "").upper() != underlying:
                continue
            if expiry is not None and trade.expiry != expiry:
                continue
            if strike is not None and (trade.strike is None or abs(float(trade.strike) - float(strike)) > 1e-9):
                continue
            if option_type and str(trade.option_type or "").upper() != option_type:
                continue
            matches.append(trade)
        except (TypeError, ValueError):
            continue

    if len(matches) != 1:
        return None

    trade = matches[0]
    response = {
        "mode": "PAPER_ONLY",
        "accepted": True,
        "request_id": record.request_id,
        "position": {
            "id": trade.id,
            "symbol": trade.symbol,
            "underlying": trade.underlying,
            "expiry": trade.expiry,
            "strike": trade.strike,
            "option_type": trade.option_type,
            "security_id": trade.security_id,
            "quantity": trade.quantity,
            "entry_price": trade.entry_price,
            "stop_price": trade.stop_price,
            "target_price": trade.target_price,
            "pnl": trade.pnl,
            "status": trade.status,
        },
        "recovered": True,
    }
    complete_request(db, record, response)
    return response
