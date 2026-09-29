from pathlib import Path


def test_option_positions_get_is_observational_and_mark_is_explicit_mutation():
    source = (
        Path(__file__).resolve().parents[1] / "app/api/v1/fno.py"
    ).read_text(encoding="utf-8")
    get_start = source.index('@router.get("/paper/positions")')
    mark_start = source.index('@router.post("/paper/positions/mark")')
    get_block = source[get_start:mark_start]
    assert "mutate=False" in get_block
    assert "update_paper_trade(db, trade, executable_price)" not in get_block
    assert '@router.post("/paper/positions/mark")' in source
