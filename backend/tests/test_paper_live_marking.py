from datetime import date

from app.services.paper_live_dhan_service import mark_dhan_paper_position


class FakeOrchestrator:
    def __init__(self):
        self.calls = []

    def summary(self):
        return {"open_position": None}


def test_ltp_mark_is_read_only_when_no_position():
    result = mark_dhan_paper_position(None, 1, FakeOrchestrator())
    assert result["reason"] == "NO_OPEN_PAPER_POSITION"
