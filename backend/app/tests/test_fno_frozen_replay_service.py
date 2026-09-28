import pytest

from app.services.fno_execution_evidence_import_service import import_execution_evidence_csv
from app.services.fno_execution_evidence_freeze_service import freeze_execution_evidence
from app.services.fno_frozen_replay_service import replay_frozen_execution_evidence


def _package(count=60):
    rows = [
        {
            "timestamp": index * 60,
            "strike": 25000,
            "option_type": "CE",
            "bid": 99.0,
            "ask": 100.0,
            "spot": 25000.0,
            "expiry": "2026-10-01",
            "security_id": "123",
            "exchange_segment": "NSE_FNO",
            "source": "vendor_x",
        }
        for index in range(count)
    ]
    raw = (
        "timestamp,strike,option_type,bid,ask,spot,expiry,security_id,exchange_segment,source\n"
        + "\n".join(
            f'{r["timestamp"]},{r["strike"]},{r["option_type"]},{r["bid"]},{r["ask"]},'
            f'{r["spot"]},{r["expiry"]},{r["security_id"]},{r["exchange_segment"]},{r["source"]}'
            for r in rows
        )
        + "\n"
    ).encode()
    manifest, quotes = import_execution_evidence_csv(
        raw,
        source="vendor_x",
        license_name="commercial-research",
        coverage_start=0,
        coverage_end=(count - 1) * 60,
        timezone="Asia/Kolkata",
        sampling_seconds=60,
        contract_universe="NIFTY weekly options",
        expected_timestamps={r["timestamp"] for r in rows},
    )
    return freeze_execution_evidence(
        manifest=manifest,
        quotes=quotes,
        expected_timestamps={r["timestamp"] for r in rows},
    )


def _bars(count=60):
    return [
        {
            "timestamp": index * 60,
            "open": 25000.0,
            "high": 25020.0,
            "low": 24980.0,
            "close": 25010.0,
        }
        for index in range(count)
    ]


def test_frozen_replay_requires_verified_package():
    package = _package()
    assert replay_frozen_execution_evidence(
        package=package,
        underlying={"symbol": "NIFTY"},
        bars=_bars(),
        lot_size=50,
    ) is not None


def test_frozen_replay_rejects_missing_timestamp():
    package = _package()
    bars = _bars()
    bars[-1]["timestamp"] = 999999
    with pytest.raises(ValueError, match="missing snapshot"):
        replay_frozen_execution_evidence(
            package=package,
            underlying={"symbol": "NIFTY"},
            bars=bars,
            lot_size=50,
        )


def test_frozen_replay_rejects_tampered_package():
    package = _package()
    object.__setattr__(package, "package_sha256", "0" * 64)
    with pytest.raises(ValueError, match="integrity"):
        replay_frozen_execution_evidence(
            package=package,
            underlying={"symbol": "NIFTY"},
            bars=_bars(),
            lot_size=50,
        )
