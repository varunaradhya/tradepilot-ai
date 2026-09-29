from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Sequence

from app.services.historical_data_service import MarketBar


@dataclass(frozen=True)
class DatasetProvenance:
    dataset_id: str
    source: str
    symbol: str
    timeframe: str
    start: str
    end: str
    row_count: int
    quality_status: str
    created_at: str
    content_fingerprint: str
    source_version: str | None = None
    import_method: str = "unknown"
    corporate_action_adjusted: bool | None = None
    quality_diagnostics: dict | None = None

    @classmethod
    def create(
        cls,
        *,
        dataset_id: str,
        source: str,
        symbol: str,
        timeframe: str,
        bars: Sequence[MarketBar],
        quality_status: str,
        content_fingerprint: str,
        source_version: str | None = None,
        import_method: str = "unknown",
        corporate_action_adjusted: bool | None = None,
        quality_diagnostics: dict | None = None,
    ) -> "DatasetProvenance":
        if not bars:
            raise ValueError("Cannot create provenance for an empty dataset")
        return cls(
            dataset_id=dataset_id,
            source=source,
            symbol=symbol.strip().upper(),
            timeframe=timeframe,
            start=bars[0].timestamp.isoformat(),
            end=bars[-1].timestamp.isoformat(),
            row_count=len(bars),
            quality_status=quality_status,
            created_at=datetime.now(timezone.utc).isoformat(),
            content_fingerprint=content_fingerprint,
            source_version=source_version,
            import_method=import_method,
            corporate_action_adjusted=corporate_action_adjusted,
            quality_diagnostics=quality_diagnostics,
        )

    def as_dict(self) -> dict:
        return asdict(self)


def fingerprint_market_bars(
    bars: Sequence[MarketBar],
    *,
    symbol: str,
    timeframe: str,
) -> str:
    """Return a deterministic SHA-256 fingerprint of normalized dataset content."""
    payload = [
        {
            "timestamp": bar.timestamp.isoformat(),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in bars
    ]
    canonical = json.dumps(
        {"symbol": symbol.strip().upper(), "timeframe": timeframe, "bars": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
