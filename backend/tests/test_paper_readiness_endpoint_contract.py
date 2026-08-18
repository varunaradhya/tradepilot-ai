from pathlib import Path


def test_paper_readiness_endpoint_does_not_accept_client_qualification_flags():
    source = Path("app/api/v1/paper_trading.py").read_text(encoding="utf-8")
    marker = 'def paper_readiness('
    start = source.index(marker)
    end = source.index('\n\n@router.get("/performance")', start)
    handler = source[start:end]

    assert "qualification_status" not in handler
    assert "robust_percent" not in handler
    assert "symbols_tested" not in handler
    assert "_server_research_readiness" in handler


def test_paper_readiness_requires_explicit_symbol_and_strategy_version():
    source = Path("app/api/v1/paper_trading.py").read_text(encoding="utf-8")
    handler = source[source.index('def paper_readiness('):]
    assert 'symbol: str = Query(min_length=1' in handler
    assert 'strategy_version: str = Query(default="V1"' in handler
