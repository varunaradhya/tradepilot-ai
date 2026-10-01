from __future__ import annotations

from collections import Counter
from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.paper_trade import PaperTrade
from app.models.paper_trade_learning import PaperTradeLearningEvent
from app.models.paper_validation_symbol import PaperValidationSymbol
from app.services.nse_equity_calendar import DEFAULT_NSE_EQUITY_CALENDAR
from app.services.paper_validation_service import validation_run_key

IST = ZoneInfo("Asia/Kolkata")


def _trade_session(trade: PaperTrade) -> str | None:
    if trade.reason and trade.reason.startswith("DHAN:"):
        parts = trade.reason.split(":")
        if len(parts) >= 2:
            try:
                return date.fromisoformat(parts[1]).isoformat()
            except ValueError:
                return None
    timestamp = trade.closed_at or trade.created_at
    return timestamp.astimezone(IST).date().isoformat() if timestamp else None


def _orphan_learning_event_ids(
    events: list[PaperTradeLearningEvent],
    all_dhan_trades: list[PaperTrade],
) -> list[int]:
    linked_ids = {
        trade.learning_event_id
        for trade in all_dhan_trades
        if trade.learning_event_id is not None
    }
    return [event.id for event in events if event.id not in linked_ids]


def reconcile_paper_learning(db: Session, user_id: int) -> dict:
    """Reconcile Dhan paper trades across trade, learning, and validation ledgers."""
    all_dhan_trades = db.query(PaperTrade).filter(
        PaperTrade.user_id == user_id,
        PaperTrade.reason.like("DHAN:%"),
    ).all()
    trades = [trade for trade in all_dhan_trades if trade.status == "CLOSED"]
    events = db.query(PaperTradeLearningEvent).filter(
        PaperTradeLearningEvent.user_id == user_id,
    ).all()

    events_by_id = {event.id: event for event in events}
    linked_event_ids = [trade.learning_event_id for trade in trades if trade.learning_event_id is not None]
    duplicate_event_ids = sorted(
        event_id for event_id, count in Counter(linked_event_ids).items() if count > 1
    )
    unlinked_trade_ids = [trade.id for trade in trades if trade.learning_event_id is None]
    broken_link_trade_ids = [
        trade.id for trade in trades
        if trade.learning_event_id is not None and trade.learning_event_id not in events_by_id
    ]

    linked_trade_ids = {trade.id for trade in trades if trade.learning_event_id in events_by_id}
    orphan_learning_event_ids = _orphan_learning_event_ids(events, all_dhan_trades)

    contamination_trade_ids: list[int] = []
    pnl_mismatch_trade_ids: list[int] = []
    evidence_missing_trade_ids: list[int] = []
    evidence_mismatch_trade_ids: list[int] = []
    invalid_calendar_trade_ids: list[int] = []
    evidence_rows_by_key: dict[tuple[str, str], PaperValidationSymbol] = {}

    for trade in trades:
        event = events_by_id.get(trade.learning_event_id)
        session = _trade_session(trade)
        key = (trade.symbol.strip().upper(), session or "")
        evidence = None
        if session:
            evidence = db.query(PaperValidationSymbol).filter(
                PaperValidationSymbol.user_id == user_id,
                PaperValidationSymbol.session_date == date.fromisoformat(session),
                PaperValidationSymbol.symbol == trade.symbol.strip().upper(),
                PaperValidationSymbol.validation_run == validation_run_key(date.fromisoformat(session)),
            ).first()
            if evidence is not None:
                evidence_rows_by_key[key] = evidence

        if session is None or not DEFAULT_NSE_EQUITY_CALENDAR.is_trading_day(date.fromisoformat(session)):
            invalid_calendar_trade_ids.append(trade.id)

        if event is None:
            continue

        if event.symbol.strip().upper() != trade.symbol.strip().upper() or event.session != session:
            contamination_trade_ids.append(trade.id)

        if abs(float(event.pnl or 0.0) - float(trade.pnl or 0.0)) > 1e-9:
            pnl_mismatch_trade_ids.append(trade.id)

        if evidence is None:
            evidence_missing_trade_ids.append(trade.id)
        elif evidence.status != "COMPLETE":
            evidence_mismatch_trade_ids.append(trade.id)

    trade_counts: dict[tuple[str, str], int] = Counter()
    trade_pnl: dict[tuple[str, str], float] = {}
    for trade in trades:
        session = _trade_session(trade)
        if session:
            key = (trade.symbol.strip().upper(), session)
            trade_counts[key] += 1
            trade_pnl[key] = trade_pnl.get(key, 0.0) + float(trade.pnl or 0.0)

    validation_mismatch_keys: list[str] = []
    for key, evidence in evidence_rows_by_key.items():
        expected_count = trade_counts.get(key, 0)
        expected_pnl = trade_pnl.get(key, 0.0)
        if evidence.trades != expected_count or abs(float(evidence.net_pnl or 0.0) - expected_pnl) > 1e-9:
            validation_mismatch_keys.append(f"{key[0]}:{key[1]}")

    closed_trade_count = len(trades)
    linked_trade_count = len(linked_trade_ids)
    all_invariants_pass = not any((
        unlinked_trade_ids,
        broken_link_trade_ids,
        duplicate_event_ids,
        orphan_learning_event_ids,
        contamination_trade_ids,
        pnl_mismatch_trade_ids,
        evidence_missing_trade_ids,
        evidence_mismatch_trade_ids,
        invalid_calendar_trade_ids,
        validation_mismatch_keys,
    ))

    return {
        "user_id": user_id,
        "closed_dhan_trades": closed_trade_count,
        "learning_events": len(events),
        "linked_trades": linked_trade_count,
        "unlinked_trade_ids": unlinked_trade_ids,
        "broken_link_trade_ids": broken_link_trade_ids,
        "duplicate_learning_event_ids": duplicate_event_ids,
        "orphan_learning_event_ids": orphan_learning_event_ids,
        "cross_symbol_or_session_trade_ids": contamination_trade_ids,
        "trade_learning_pnl_mismatch_ids": pnl_mismatch_trade_ids,
        "missing_validation_evidence_trade_ids": evidence_missing_trade_ids,
        "incomplete_validation_evidence_trade_ids": evidence_mismatch_trade_ids,
        "invalid_calendar_trade_ids": invalid_calendar_trade_ids,
        "validation_count_or_pnl_mismatch_keys": validation_mismatch_keys,
        "reconciled": all_invariants_pass,
        "invariants": {
            "closed_trade_has_exactly_one_learning_event": not unlinked_trade_ids and not broken_link_trade_ids and not duplicate_event_ids,
            "no_orphan_learning_events": not orphan_learning_event_ids,
            "trade_learning_symbol_session_match": not contamination_trade_ids,
            "trade_learning_pnl_match": not pnl_mismatch_trade_ids,
            "validation_evidence_exists_and_is_complete": not evidence_missing_trade_ids and not evidence_mismatch_trade_ids,
            "validation_session_is_nse_trading_day": not invalid_calendar_trade_ids,
            "validation_trade_count_and_pnl_match": not validation_mismatch_keys,
        },
        "evidence_is_descriptive": True,
        "live_execution_enabled": False,
    }
