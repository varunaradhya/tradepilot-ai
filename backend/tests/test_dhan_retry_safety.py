from pathlib import Path


def test_broker_order_placement_disables_automatic_retries():
    source = Path("app/brokers/dhan.py").read_text(encoding="utf-8")
    start = source.index("    def place_order(")
    end = source.index("\n    def get_order(", start)
    section = source[start:end]
    assert "allow_retries=False" in section
    assert "retry" in section.lower()


def test_dhan_request_has_explicit_retry_policy():
    source = Path("app/brokers/dhan.py").read_text(encoding="utf-8")
    assert "allow_retries: bool = True" in source
    assert "retry_limit = self.max_retries if allow_retries else 0" in source


def test_dhan_errors_do_not_persist_provider_response_payloads():
    from pathlib import Path
    source = Path("app/brokers/dhan.py").read_text(encoding="utf-8")
    assert "Dhan API returned HTTP" in source
    assert "print(" not in source
    assert 'logger.warning("Dhan connection retry' in source
