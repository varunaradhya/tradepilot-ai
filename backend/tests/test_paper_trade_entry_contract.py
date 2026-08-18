from pathlib import Path


def test_direct_paper_trade_creation_is_disabled():
    source = Path("app/api/v1/paper_trading.py").read_text(encoding="utf-8")
    marker = 'def create_paper_trade('
    start = source.index(marker)
    end = source.index('\n\n@router.get("/trades")', start)
    handler = source[start:end]

    assert "Direct paper-trade creation is disabled" in handler
    assert "open_paper_trade(" not in handler
    assert "HTTP_405_METHOD_NOT_ALLOWED" in handler
