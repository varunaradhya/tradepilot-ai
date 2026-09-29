from pathlib import Path


def _source() -> str:
    return Path("app/api/v1/paper_trading.py").read_text(encoding="utf-8")


def test_paper_signal_requires_persisted_authorization():
    source = _source()
    start = source.index('def paper_session_signal(')
    end = source.index('\n\n@router.post("/session/bar")', start)
    handler = source[start:end]
    assert "_load_authorization" in handler
    assert "HTTP_403_FORBIDDEN" in handler
    assert "payload.strategy_version" in handler
    assert "payload.symbol" in handler


def test_market_and_dhan_entry_paths_require_persisted_authorization():
    source = _source()
    for marker, end_marker in [
        ('def paper_market_bar(', '\n\n@router.post("/session/dhan")'),
        ('def paper_dhan_session(', '\n\n@router.post("/session/market-reset")'),
    ]:
        start = source.index(marker)
        end = source.index(end_marker, start)
        handler = source[start:end]
        assert "_load_authorization" in handler
        assert "HTTP_403_FORBIDDEN" in handler


def test_readiness_authorization_is_server_owned():
    source = _source()
    assert '@router.post("/readiness/authorize")' in source
    assert "authorize_strategy(db" in source
    assert "strategy_fingerprint" in source



def test_legacy_paper_session_mutations_are_disabled():
    source = Path("app/api/v1/paper_session.py").read_text(encoding="utf-8")
    assert 'status.HTTP_410_GONE' in source
    assert 'Legacy paper-session mutation is disabled' in source
    assert 'Legacy paper-session reset is disabled' in source


def test_main_paper_router_legacy_mutations_are_disabled():
    source = _source()
    assert 'detail="Legacy paper-session bar mutation is disabled' in source
    assert 'detail="Legacy paper-session reset is disabled' in source
    assert 'detail="Paper market-state reset is disabled' in source


def test_fno_execution_adapter_is_fail_closed():
    source = Path("app/services/fno_execution.py").read_text(encoding="utf-8")
    assert "LIVE_EXECUTION_DISABLED" in source
    assert "client.place_order" not in source
    assert "TRADEPILOT_LIVE_EXECUTION_ENABLED" not in source


def test_fno_paper_entry_requires_persisted_strategy_authorization():
    source = Path("app/api/v1/fno.py").read_text(encoding="utf-8")
    start = source.index('def open_option_paper_trade(')
    end = source.index('\n\n@router.get("/paper/recovery")', start)
    handler = source[start:end]
    assert "get_active_authorization" in handler
    assert "No active qualified strategy authorization" in handler
    assert "decision_fingerprint" in handler
    assert "authorization.fingerprint" in handler


def test_direct_paper_trade_mutations_lock_owned_rows():
    source = Path("app/api/v1/paper_trading.py").read_text(encoding="utf-8")
    start = source.index("def _owned(")
    end = source.index("\n\n\ndef _orchestrator", start)
    owned = source[start:end]
    assert ".with_for_update()" in owned
    assert "PaperTrade.user_id == user_id" in owned
