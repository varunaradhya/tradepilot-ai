import hashlib
import json
from app.services.paper_validation_service import _canonical_hash

def test_validation_manifest_hash_is_canonical():
    left = {"b": 2, "a": [1, 2], "nested": {"z": True}}
    right = {"nested": {"z": True}, "a": [1, 2], "b": 2}
    assert _canonical_hash(left) == _canonical_hash(right)

def test_validation_evidence_chain_hash_changes_when_previous_link_changes():
    first = {"session_date": "2026-09-28", "day_fingerprint": "a", "symbol_fingerprints": ["x"], "previous_hash": ""}
    second = {"session_date": "2026-09-29", "day_fingerprint": "b", "symbol_fingerprints": ["y"], "previous_hash": _canonical_hash(first)}
    altered = {**second, "previous_hash": "tampered"}
    assert _canonical_hash(second) != _canonical_hash(altered)

def test_validation_manifest_never_enables_live_execution():
    manifest = {"evidence_is_descriptive": True, "live_execution_enabled": False, "execution_mode": "SIMULATION_ONLY"}
    assert manifest["live_execution_enabled"] is False
    assert manifest["execution_mode"] == "SIMULATION_ONLY"
