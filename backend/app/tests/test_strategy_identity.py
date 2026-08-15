from dataclasses import dataclass

from app.services.strategy_identity import strategy_fingerprint, strategy_identity


@dataclass(frozen=True)
class SampleStrategy:
    fast_period: int = 9
    slow_period: int = 20
    reward_multiple: float = 2.0


def test_fingerprint_is_deterministic():
    first = strategy_fingerprint(SampleStrategy(), strategy_version="V1", execution={"slippage_rate": 0.0005})
    second = strategy_fingerprint(SampleStrategy(), strategy_version="V1", execution={"slippage_rate": 0.0005})
    assert first == second
    assert len(first) == 16


def test_fingerprint_changes_when_execution_assumption_changes():
    first = strategy_fingerprint(SampleStrategy(), strategy_version="V1", execution={"slippage_rate": 0.0005})
    second = strategy_fingerprint(SampleStrategy(), strategy_version="V1", execution={"slippage_rate": 0.001})
    assert first != second


def test_identity_contains_version_and_fingerprint():
    result = strategy_identity(SampleStrategy(), strategy_version="V2")
    assert result["strategy_version"] == "V2"
    assert isinstance(result["fingerprint"], str)
