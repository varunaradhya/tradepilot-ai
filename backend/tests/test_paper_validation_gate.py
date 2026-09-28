from datetime import date
from app.services.paper_validation_gate import evaluate_validation_gate

def test_validation_gate_requires_complete_manifest():
    class ReportQuery:
        def __init__(self): self.status = "PENDING"
    class FakeDB:
        def query(self, model):
            return self
        def filter(self, *args, **kwargs):
            return self
        def order_by(self, *args, **kwargs):
            return self
        def all(self):
            return []
        def first(self):
            return None

    gate = evaluate_validation_gate(FakeDB(), 1, "P10_2026-09-28_30D")
    assert gate.passed is False
    assert gate.completed_sessions == 0
    assert gate.manifest_valid is False
    assert "THIRTY_COMPLETE_NSE_SESSIONS_REQUIRED" in gate.reasons
    assert "VALIDATION_MANIFEST_MISSING" in gate.reasons
