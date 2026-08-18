from __future__ import annotations


def assert_paper_state_consistent(reconciliation: dict) -> None:
    if reconciliation.get("status") != "CONSISTENT":
        raise RuntimeError("Paper trading state reconciliation failed; simulation halted")
