from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from app.brokers.base import BrokerHolding
from app.models.holding import Holding


def reconcile_holdings(
    holdings: Iterable[Holding],
    broker_holdings: Iterable[BrokerHolding],
    broker_name: str,
) -> dict:
    tp = {h.symbol.upper(): h for h in holdings}
    br = {h.symbol.upper(): h for h in broker_holdings}

    symbols = sorted(set(tp) | set(br))
    items = []

    matched = quantity_mismatches = average_mismatches = 0
    missing_tp = missing_br = 0

    for symbol in symbols:
        t = tp.get(symbol)
        b = br.get(symbol)

        tq = Decimal(str(t.quantity)) if t else Decimal("0")
        bq = Decimal(str(b.quantity)) if b else Decimal("0")
        tap = Decimal(str(t.average_buy_price)) if t else Decimal("0")
        bap = Decimal(str(b.average_price)) if b else Decimal("0")

        qdiff = tq - bq
        pdiff = tap - bap

        if t is None:
            status = "MISSING_FROM_TRADEPILOT"
            missing_tp += 1
        elif b is None:
            status = "MISSING_FROM_BROKER"
            missing_br += 1
        elif qdiff != 0:
            status = "QUANTITY_MISMATCH"
            quantity_mismatches += 1
        elif abs(pdiff) > Decimal("0.01"):
            status = "AVERAGE_PRICE_MISMATCH"
            average_mismatches += 1
        else:
            status = "MATCHED"
            matched += 1

        items.append(
            {
                "symbol": symbol,
                "tradepilot_quantity": float(tq),
                "broker_quantity": float(bq),
                "quantity_difference": float(qdiff),
                "tradepilot_average_price": float(tap),
                "broker_average_price": float(bap),
                "average_price_difference": float(pdiff),
                "status": status,
            }
        )

    return {
        "broker": broker_name,
        "summary": {
            "matched": matched,
            "quantity_mismatches": quantity_mismatches,
            "average_price_mismatches": average_mismatches,
            "missing_from_tradepilot": missing_tp,
            "missing_from_broker": missing_br,
        },
        "items": items,
    }