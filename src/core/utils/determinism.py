from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable, List

from src.core.models import HoldingInput


def stable_sort_holdings(holdings: Iterable[HoldingInput]) -> List[HoldingInput]:
    return sorted(holdings, key=lambda holding: holding.identity.holding_id)


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
