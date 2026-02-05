from __future__ import annotations

from src.core.models import HoldingIdentity, HoldingInput
from src.core.utils.determinism import stable_sort_holdings


def test_stable_sort_holdings_orders_by_holding_id():
    holdings = [
        HoldingInput(identity=HoldingIdentity(holding_id="B", ticker="BBB"), weight=0.5),
        HoldingInput(identity=HoldingIdentity(holding_id="A", ticker="AAA"), weight=0.5),
    ]

    ordered = stable_sort_holdings(holdings)

    assert [holding.identity.holding_id for holding in ordered] == ["A", "B"]
