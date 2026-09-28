from __future__ import annotations

from typing import Any

from app.services.intraday_strategy import IntradayConfig
from app.services.paper_trading_orchestrator import PaperOrchestratorConfig, PaperTradingOrchestrator
from app.services.paper_market_service import PaperMarketCoordinator


def run_paper_replay(rows: list[dict[str, Any]], *, session: str, symbol: str, strategy: IntradayConfig | None = None) -> dict[str, Any]:
    if not rows:
        return {"mode": "SIMULATION_ONLY", "processed_bars": 0, "trades": [], "metrics": _metrics([])}
    strategy = strategy or IntradayConfig(trade_direction="LONG_ONLY")
    # Replay is a research/simulation path. It deliberately uses a fresh engine and
    # never changes the user's qualified live paper session or broker state.
    orchestrator = PaperTradingOrchestrator(PaperOrchestratorConfig(trade_direction="LONG_ONLY", qualification_required=False))
    coordinator = PaperMarketCoordinator(orchestrator=orchestrator, strategy=strategy)
    processed = 0
    for row in rows:
        coordinator.on_bar(
            session=session, symbol=symbol,
            open_price=float(row["open"]), high=float(row["high"]), low=float(row["low"]),
            close=float(row["close"]), volume=float(row.get("volume", 0)),
            opening_high=row.get("opening_high"), opening_low=row.get("opening_low"),
        )
        processed += 1
    last_close = float(rows[-1]["close"])
    coordinator.close_session(session, symbol, last_close)
    trades = coordinator.orchestrator.trades()
    return {"mode": "SIMULATION_ONLY", "symbol": symbol.strip().upper(), "session": session, "processed_bars": processed, "trades": trades, "metrics": _metrics(trades)}


def _metrics(trades: list[dict[str, Any]]) -> dict[str, float]:
    pnl = [float(t.get("pnl", 0.0)) for t in trades]
    winners = [x for x in pnl if x > 0]
    losers = [x for x in pnl if x < 0]
    gross_profit = sum(winners)
    gross_loss = abs(sum(losers))
    r_values = [float(t.get("r_multiple", 0.0)) for t in trades if t.get("r_multiple") is not None]
    peak = 0.0
    equity = 0.0
    max_drawdown = 0.0
    for value in pnl:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return {
        "trades": float(len(trades)),
        "win_rate_percent": round(len(winners) / len(trades) * 100, 2) if trades else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else (999.0 if gross_profit else 0.0),
        "net_pnl": round(sum(pnl), 2),
        "avg_r": round(sum(r_values) / len(r_values), 4) if r_values else 0.0,
        "max_drawdown": round(max_drawdown, 2),
        "expectancy": round(sum(pnl) / len(pnl), 2) if pnl else 0.0,
    }
