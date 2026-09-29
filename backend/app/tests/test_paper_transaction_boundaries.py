from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_paper_signal_claim_supports_deferred_commit():
    source = _read("app/services/paper_signal_request_service.py")
    assert "commit: bool = True" in source
    assert "if commit:" in source
    assert "db.flush()" in source


def test_paper_signal_route_claims_request_inside_mutation_transaction():
    source = _read("app/api/v1/paper_trading.py")
    lock = source.index("_lock_paper_state(db, current_user.id)")
    claim = source.index("claim_request(db, current_user.id, request_id, signal, commit=False)")
    assert lock < claim
    assert "complete_request(db, record, response, commit=False)" in source
    assert "db.commit()" in source[claim:claim + 5000]


def test_authorization_mutations_share_paper_state_lock():
    source = _read("api/v1/paper_trading.py")
    authorize = source.index("def authorize_paper_readiness")
    revoke = source.index("def revoke_paper_readiness")
    assert "_lock_paper_state(db, current_user.id)" in source[authorize:revoke]
    assert "_lock_paper_state(db, current_user.id)" in source[revoke:source.index("def get_paper_performance")]
    

def test_dhan_replay_defers_validation_evidence_commit_until_trade_persistence():
    source = _read("app/services/paper_dhan_service.py")
    assert 'record_validation_symbol(' in source
    assert 'commit=False' in source
    assert 'complete_validation_day(db, user_id, run_key, trading_day, diagnostics, commit=False)' in source
    assert source.rfind("db.commit()") > source.rfind("complete_validation_day(")


def test_validation_service_supports_deferred_commit():
    source = _read("app/services/paper_validation_service.py")
    assert "record_validation_symbol" in source and "commit: bool = True" in source
    assert "record_validation_day" in source and "commit: bool = True" in source
    assert "complete_validation_day" in source and "commit: bool = True" in source
