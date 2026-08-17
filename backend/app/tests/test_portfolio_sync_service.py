import app.services.portfolio_sync_service as service


class FakeColumn:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return lambda row: getattr(row, self.name) == other


class FakeHolding:
    user_id = FakeColumn("user_id")
    symbol = FakeColumn("symbol")

    def __init__(self, symbol, quantity, average_buy_price, user_id=1):
        self.user_id = user_id
        self.symbol = symbol
        self.quantity = quantity
        self.average_buy_price = average_buy_price


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *predicates):
        for predicate in predicates:
            if callable(predicate):
                self.rows = [row for row in self.rows if predicate(row)]
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return list(self.rows)


class FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.added = []
        self.deleted = []

    def query(self, model):
        return FakeQuery(self.rows)

    def add(self, value):
        self.added.append(value)

    def delete(self, value):
        self.deleted.append(value)


def test_sync_holdings_removes_stale_positions():
    stale = FakeHolding("OLD", 10, 100)
    current = FakeHolding("TCS", 5, 3000)
    db = FakeDB([stale, current])
    original = service.Holding
    service.Holding = FakeHolding
    try:
        updated = service._sync_holdings(
            db,
            1,
            [{"tradingSymbol": "TCS", "totalQty": 7, "avgCostPrice": 3100}],
        )
    finally:
        service.Holding = original
    assert updated == 1
    assert stale in db.deleted
    assert current.quantity == 7
    assert current.average_buy_price == 3100


def test_sync_holdings_empty_snapshot_clears_positions():
    stale = FakeHolding("OLD", 10, 100)
    db = FakeDB([stale])
    original = service.Holding
    service.Holding = FakeHolding
    try:
        updated = service._sync_holdings(db, 1, [])
    finally:
        service.Holding = original
    assert updated == 0
    assert stale in db.deleted
