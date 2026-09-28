from __future__ import annotations
from dataclasses import dataclass
from app.services.paper_validation_service import VALIDATION_DAYS, build_validation_report, verify_validation_manifest

@dataclass(frozen=True)
class ValidationGate:
    passed: bool
    reasons: tuple[str, ...]
    required_sessions: int
    completed_sessions: int
    manifest_valid: bool
    live_execution_enabled: bool = False

def evaluate_validation_gate(db, user_id: int, run_key: str) -> ValidationGate:
    report = build_validation_report(db, user_id, run_key)
    progress = report["progress"]
    verification = verify_validation_manifest(db, user_id, run_key)
    reasons = []
    if progress["completed_sessions"] < VALIDATION_DAYS:
        reasons.append("THIRTY_COMPLETE_NSE_SESSIONS_REQUIRED")
    if not progress["complete"]:
        reasons.append("VALIDATION_RUN_INCOMPLETE")
    if not verification.get("exists"):
        reasons.append("VALIDATION_MANIFEST_MISSING")
    elif not verification.get("valid"):
        reasons.append("VALIDATION_MANIFEST_TAMPERED_OR_STALE")
    if report.get("live_execution_enabled") is not False:
        reasons.append("LIVE_EXECUTION_MUST_REMAIN_DISABLED")
    return ValidationGate(
        passed=not reasons,
        reasons=tuple(reasons),
        required_sessions=VALIDATION_DAYS,
        completed_sessions=progress["completed_sessions"],
        manifest_valid=bool(verification.get("valid")),
    )

def validation_readiness(db, user_id: int, run_key: str) -> dict:
    gate = evaluate_validation_gate(db, user_id, run_key)
    return {
        "ready": gate.passed,
        "status": "VALIDATION_COMPLETE" if gate.passed else "VALIDATION_PENDING",
        "required_sessions": gate.required_sessions,
        "completed_sessions": gate.completed_sessions,
        "remaining_sessions": max(gate.required_sessions - gate.completed_sessions, 0),
        "manifest_valid": gate.manifest_valid,
        "reasons": list(gate.reasons),
        "evidence_is_descriptive": True,
        "live_execution_enabled": False,
        "execution_mode": "SIMULATION_ONLY",
    }
