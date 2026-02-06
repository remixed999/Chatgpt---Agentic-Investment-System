from __future__ import annotations

import json
import math
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel

from src.core.canonicalization.rules import EXCLUDED_FIELDS, ORDERING_RULES, TRIM_FIELDS


class _ExcludeType:
    pass


EXCLUDE = _ExcludeType()


def canonicalize_payload(payload: Any) -> Any:
    return _canonicalize_value(payload, parent_key=None)


def _canonicalize_value(value: Any, parent_key: Optional[str]) -> Any:
    if isinstance(value, BaseModel):
        return _canonicalize_value(value.model_dump(), parent_key=parent_key)
    if isinstance(value, dict):
        return _canonicalize_dict(value)
    if isinstance(value, list):
        return _canonicalize_list(value, parent_key)
    if isinstance(value, tuple):
        return _canonicalize_list(list(value), parent_key)
    if isinstance(value, str) and parent_key in TRIM_FIELDS:
        return value.strip()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return EXCLUDE
        return value
    return value


def _canonicalize_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    canonical: Dict[str, Any] = {}
    for key, value in payload.items():
        if key in EXCLUDED_FIELDS:
            continue
        canonical_value = _canonicalize_value(value, parent_key=key)
        if canonical_value is EXCLUDE:
            continue
        canonical[key] = canonical_value
    return canonical


def _canonicalize_list(values: Iterable[Any], parent_key: Optional[str]) -> List[Any] | _ExcludeType:
    normalized: List[Any] = []
    for value in values:
        canonical_value = _canonicalize_value(value, parent_key=None)
        if canonical_value is EXCLUDE:
            continue
        normalized.append(canonical_value)

    if parent_key and parent_key in ORDERING_RULES:
        ordering = ORDERING_RULES[parent_key]
        ordered = ordering([item for item in normalized if isinstance(item, dict)])
        if ordered is None:
            return EXCLUDE
        return [item for item in ordered]

    return normalized


def canonicalization_idempotent(payload: Any) -> bool:
    canonical = canonicalize_payload(payload)
    return canonicalize_payload(canonical) == canonical


def detect_ordering_violations(payload: Any) -> List[str]:
    violations: List[str] = []

    def _walk(value: Any, parent_key: Optional[str], path: str) -> None:
        if isinstance(value, BaseModel):
            _walk(value.model_dump(), parent_key, path)
            return
        if isinstance(value, dict):
            for key, nested in value.items():
                if key in EXCLUDED_FIELDS:
                    continue
                next_path = f"{path}.{key}" if path else key
                _walk(nested, key, next_path)
            return
        if isinstance(value, (list, tuple)):
            list_value = list(value)
            if parent_key and parent_key in ORDERING_RULES:
                if any(not isinstance(item, dict) for item in list_value):
                    violations.append(path or parent_key)
                else:
                    normalized = [canonicalize_payload(item) for item in list_value]
                    ordering = ORDERING_RULES[parent_key]
                    ordered = ordering(normalized)
                    if ordered is None:
                        violations.append(path or parent_key)
                    elif list(ordered) != normalized:
                        violations.append(path or parent_key)
            for index, item in enumerate(list_value):
                next_path = f"{path}[{index}]" if path else f"[{index}]"
                _walk(item, None, next_path)

    _walk(payload, None, "")
    return violations


def canonical_json_dumps(payload: Any) -> str:
    canonical = canonicalize_payload(payload)
    return _encode_json(canonical)


def _encode_json(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return _format_float(value)
    if isinstance(value, Decimal):
        return _format_decimal(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, datetime):
        return json.dumps(value.isoformat(), ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, dict):
        items = []
        for key in sorted(value.keys()):
            encoded_key = json.dumps(key, ensure_ascii=False, separators=(",", ":"))
            encoded_value = _encode_json(value[key])
            items.append(f"{encoded_key}:{encoded_value}")
        return "{" + ",".join(items) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_encode_json(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _format_float(value: float) -> str:
    return _format_decimal(Decimal(str(value)))


def _format_decimal(value: Decimal) -> str:
    normalized = format(value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if normalized in {"-0", "-0.0"}:
        normalized = "0"
    return normalized
