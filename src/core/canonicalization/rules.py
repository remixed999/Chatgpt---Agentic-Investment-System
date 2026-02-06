from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Optional, Tuple


EXCLUDED_FIELDS = {
    "run_id",
    "generated_at",
    "retrieval_timestamp",
    "notes",
    "disclaimers",
    "limitations",
}


def sort_holdings(items: Iterable[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Any], ...]]:
    return tuple(
        sorted(
            items,
            key=lambda item: (
                (item.get("identity") or {}).get("holding_id")
                or item.get("holding_id")
                or ""
            ),
        )
    )


def sort_agent_outputs(items: Iterable[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Any], ...]]:
    return tuple(sorted(items, key=lambda item: item.get("agent_name", "")))


def sort_penalty_items(items: Iterable[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Any], ...]]:
    return tuple(
        sorted(
            items,
            key=lambda item: (
                item.get("category", ""),
                item.get("reason", ""),
                item.get("source_agent", ""),
            ),
        )
    )


def sort_veto_logs(items: Iterable[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Any], ...]]:
    if any(item.get("sequence_number") is None for item in items):
        return None
    return tuple(
        sorted(
            items,
            key=lambda item: (
                item.get("sequence_number", 0),
                item.get("agent_name", ""),
                item.get("rule_id", ""),
            ),
        )
    )


ORDERING_RULES: Dict[str, Callable[[Iterable[Dict[str, Any]]], Optional[Tuple[Dict[str, Any], ...]]]] = {
    "holdings": sort_holdings,
    "agent_outputs": sort_agent_outputs,
    "penalty_items": sort_penalty_items,
    "veto_logs": sort_veto_logs,
}
