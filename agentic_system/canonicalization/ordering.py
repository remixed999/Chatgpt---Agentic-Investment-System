from __future__ import annotations

import math
from dataclasses import is_dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence


# DD-07: deterministic ordering + canonical serialization

_EXCLUDED_FIELDS = {
    "run_id",
    "start_time",
    "end_time",
    "generated_at",
    "retrieval_timestamp",
    "duration_seconds",
    "notes",
    "limitations",
    "disclaimers",
    "recovery_suggestions",
}


class CanonicalizationError(ValueError):
    pass


def _normalize_number(value: float | int | Decimal) -> str:
    decimal_value = Decimal(str(value))
    if decimal_value.is_nan() or decimal_value.is_infinite():
        return "null"
    string_value = format(decimal_value, "f")
    if "." in string_value:
        string_value = string_value.rstrip("0").rstrip(".")
    if string_value == "-0":
        string_value = "0"
    return string_value


def _canonical_key(item: Any) -> tuple:
    if isinstance(item, Mapping):
        if "holding_id" in item:
            return ("holding_id", str(item["holding_id"]))
        if "agent_name" in item:
            return ("agent_name", str(item["agent_name"]))
        if all(key in item for key in ("category", "reason", "source_agent")):
            return (
                "penalty",
                str(item["category"]),
                str(item["reason"]),
                str(item["source_agent"]),
            )
    return ("value", repr(item))


def _sort_sequence(items: Sequence[Any]) -> list[Any]:
    return sorted(items, key=_canonical_key)


def _to_primitive(value: Any) -> Any:
    if is_dataclass(value):
        return {
            key: _to_primitive(getattr(value, key))
            for key in value.__dataclass_fields__
            if key not in _EXCLUDED_FIELDS
        }
    if isinstance(value, Mapping):
        return {
            key: _to_primitive(item)
            for key, item in value.items()
            if key not in _EXCLUDED_FIELDS
        }
    if isinstance(value, (list, tuple)):
        return [_to_primitive(item) for item in _sort_sequence(value)]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    return value


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        return _normalize_number(value)
    if isinstance(value, str):
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'
    if isinstance(value, Mapping):
        items = []
        for key in sorted(value.keys()):
            items.append(f'{_serialize(str(key))}:{_serialize(value[key])}')
        return "{" + ",".join(items) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_serialize(item) for item in value) + "]"
    raise CanonicalizationError(f"Unsupported type in canonicalization: {type(value)}")


def canonicalize_payload(payload: Any) -> str:
    primitive = _to_primitive(payload)
    return _serialize(primitive)

