from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_paper_router_does_not_keep_process_local_mutable_session_state():
    source = (ROOT / "app/api/v1/paper_trading.py").read_text(encoding="utf-8")
    assert "_sessions:" not in source
    assert "_market:" not in source
    assert "_restored:" not in source
    assert "Build a request-scoped orchestrator from durable state" in source


def test_paper_mutations_lock_the_user_state_boundary():
    source = (ROOT / "app/api/v1/paper_trading.py").read_text(encoding="utf-8")
    assert "def _lock_paper_state" in source
    assert ".with_for_update()" in source
    assert "_lock_paper_state(db, current_user.id)" in source


def test_signal_and_market_bar_keep_intermediate_writes_uncommitted():
    source = (ROOT / "app/api/v1/paper_trading.py").read_text(encoding="utf-8")
    assert "persist=True, commit=False" in source
    assert 'payload.interval, "V1", commit=False' in source


def test_ml_prediction_supports_deferred_commit():
    source = (ROOT / "app/services/paper_ml_service.py").read_text(encoding="utf-8")
    assert "commit: bool = True" in source
    assert "if commit:" in source


def test_market_state_supports_deferred_commit():
    source = (ROOT / "app/services/paper_market_state_service.py").read_text(encoding="utf-8")
    assert "commit: bool = True" in source
    assert "if commit:" in source
