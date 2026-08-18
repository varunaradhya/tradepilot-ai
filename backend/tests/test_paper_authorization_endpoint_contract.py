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
