from app.services.fno_execution_evidence_import_service import import_execution_evidence_csv
from app.services.fno_execution_evidence_freeze_service import freeze_execution_evidence
from app.services.fno_qualification_service import QualificationConfig, qualify_walk_forward

CSV = (
    "timestamp,strike,option_type,bid,ask,spot,expiry,security_id,exchange_segment,source\n"
    "100,25000,CE,99.5,100,25010,2026-10-01,123,NSE_FNO,vendor_x\n"
).encode()


def _trades(values):
    return [{"pnl": value} for value in values]


def _evidence():
    manifest, quotes = import_execution_evidence_csv(
        CSV,
        source="vendor_x",
        license_name="commercial-research",
        coverage_start=100,
        coverage_end=100,
        timezone="Asia/Kolkata",
        sampling_seconds=60,
        contract_universe="NIFTY weekly options",
        expected_timestamps={100},
    )
    return freeze_execution_evidence(
        manifest=manifest, quotes=quotes, expected_timestamps={100}
    )


def test_walk_forward_requires_oos_evidence():
    result = qualify_walk_forward(
        in_sample_trades=_trades([100.0] * 30),
        out_of_sample_trades=[],
    )
    assert result["qualified"] is False
    assert result["gates"]["oos_min_trades"] is False


def test_walk_forward_requires_verifiable_execution_package():
    result = qualify_walk_forward(
        in_sample_trades=_trades([100.0] * 30),
        out_of_sample_trades=_trades([80.0] * 10),
    )
    assert result["qualified"] is False
    assert result["gates"]["execution_grade_evidence"] is False


def test_walk_forward_uses_verified_frozen_evidence():
    result = qualify_walk_forward(
        in_sample_trades=_trades([100.0] * 20 + [-50.0] * 10),
        out_of_sample_trades=_trades([80.0] * 10),
        config=QualificationConfig(
            min_trades=30, min_oos_trades=10, min_profit_factor=1.2,
            max_drawdown_percent=30.0
        ),
        execution_evidence_package=_evidence(),
    )
    assert result["qualified"] is True
    assert result["gates"]["execution_grade_evidence"] is True
    assert result["in_sample"]["trades"] == 30
    assert result["evidence"]["package_sha256"] == _evidence().package_sha256


def test_walk_forward_rejects_tampered_execution_package():
    package = _evidence()
    object.__setattr__(package, "package_sha256", "0" * 64)
    result = qualify_walk_forward(
        in_sample_trades=_trades([100.0] * 30),
        out_of_sample_trades=_trades([80.0] * 10),
        execution_evidence_package=package,
    )
    assert result["qualified"] is False
    assert result["gates"]["execution_grade_evidence"] is False


def test_walk_forward_rejects_excessive_drawdown():
    result = qualify_walk_forward(
        in_sample_trades=_trades([100.0] * 30),
        out_of_sample_trades=_trades([100.0, -1000.0] * 5),
        config=QualificationConfig(min_trades=30, min_oos_trades=10, max_drawdown_percent=20.0),
    )
    assert result["qualified"] is False
    assert result["gates"]["oos_drawdown"] is False
