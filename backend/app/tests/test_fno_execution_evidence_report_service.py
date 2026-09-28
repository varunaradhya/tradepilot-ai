from app.services.fno_execution_evidence_import_service import import_execution_evidence_csv
from app.services.fno_execution_evidence_freeze_service import freeze_execution_evidence
from app.services.fno_execution_evidence_report_service import build_execution_evidence_report

RAW = (
    "timestamp,strike,option_type,bid,ask,spot,expiry,security_id,exchange_segment,source\n"
    "100,25000,CE,99,100,25010,2026-10-01,123,NSE_FNO,vendor_x\n"
    "160,25000,PE,101,102,25010,2026-10-01,124,NSE_FNO,vendor_x\n"
).encode()


def test_execution_evidence_report_is_descriptive_and_verified():
    manifest, quotes = import_execution_evidence_csv(
        RAW,
        source="vendor_x",
        license_name="commercial-research",
        coverage_start=100,
        coverage_end=160,
        timezone="Asia/Kolkata",
        sampling_seconds=60,
        contract_universe="NIFTY weekly options",
        expected_timestamps={100, 160},
    )
    package = freeze_execution_evidence(
        manifest=manifest, quotes=quotes, expected_timestamps={100, 160}
    )
    report = build_execution_evidence_report(package)
    assert report["verified"] is True
    assert report["quote_count"] == 2
    assert report["contract_count"] == 2
    assert report["coverage"]["timestamp_count"] == 2
    assert report["package_sha256"] == package.package_sha256
