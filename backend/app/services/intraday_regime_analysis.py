from __future__ import annotations

from collections import Counter
from typing import Sequence

from app.services.market_regime import classify_market_regime


def _returns(values: Sequence[float]) -> float:
    if len(values) < 2 or values[0] <= 0:
        return 0.0
    return (values[-1] / values[0] - 1.0) * 100.0


def _sort_key(row: dict):
    """Return a comparable chronological key for common timestamp fields."""
    value = row.get("timestamp") or row.get("datetime") or row.get("date")
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def build_benchmark_regime_analysis(benchmark_rows: Sequence[dict], lookback: int = 50, step: int = 25) -> dict:
    """Describe a benchmark's chronological regimes without fitting anything.

    Historical rows are normalized into chronological order before rolling
    windows are built. This prevents an unsorted provider response from
    corrupting the temporal sequence while preserving look-ahead protection:
    each observation still uses only rows at or before its own timestamp.
    """
    if lookback < 20 or step < 1:
        raise ValueError("lookback must be >= 20 and step must be >= 1")
    rows = sorted(benchmark_rows, key=_sort_key)
    if len(rows) < lookback:
        return {"status": "INSUFFICIENT_DATA", "observations": [], "distribution": {}}
    observations: list[dict] = []
    for end in range(lookback, len(rows) + 1, step):
        window = rows[end - lookback:end]
        closes = [float(row["close"]) for row in window]
        regime = classify_market_regime(closes, lookback=lookback)
        observations.append({
            "timestamp": window[-1].get("timestamp") or window[-1].get("datetime") or window[-1].get("date"),
            "label": regime.label,
            "trend_score": regime.trend_score,
            "momentum_percent": regime.momentum_percent,
            "volatility_percent": regime.volatility_percent,
            "confidence": regime.confidence,
            "window_return_percent": round(_returns(closes), 4),
        })
    counts = Counter(item["label"] for item in observations)
    total = len(observations)
    distribution = {label: {"observations": count, "percent": round(count / total * 100, 2)} for label, count in sorted(counts.items())}
    return {
        "status": "OK",
        "lookback": lookback,
        "step": step,
        "observations": observations,
        "distribution": distribution,
        "method": "rolling_chronological_benchmark_regime",
        "optimization_performed": False,
        "lookahead_bias_protection": True,
    }
