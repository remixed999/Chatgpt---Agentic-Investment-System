from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable, List, Tuple

from src.core.models import HoldingInput


def _holding_sort_key(index: int, holding: HoldingInput) -> Tuple[str, int]:
    holding_id = ""
    if holding.identity and holding.identity.holding_id:
        holding_id = holding.identity.holding_id
    return (holding_id, index)


def stable_sort_holdings(holdings: Iterable[HoldingInput]) -> List[HoldingInput]:
    indexed = list(enumerate(holdings))
    ordered = sorted(indexed, key=lambda item: _holding_sort_key(item[0], item[1]))
    return [holding for _, holding in ordered]


def _default_serializer(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def stable_json_dumps(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_default_serializer,
    )
