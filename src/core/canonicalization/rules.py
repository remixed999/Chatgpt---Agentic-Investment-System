from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Optional, Tuple


EXCLUDED_FIELDS = {
    "run_id",
    "runlog_ref",
    "start_time",
    "end_time",
    "generated_at",
    "retrieval_timestamp",
    "veto_logs",
    "notes",
    "disclaimers",
    "limitations",
    "recovery_suggestions",
    "snapshot_hash",
    "config_hash",
    "run_config_hash",
    "committee_packet_hash",
    "decision_hash",
    "run_hash",
}

TRIM_FIELDS = {
    "holding_id",
    "agent_name",
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


def sort_concentration_breaches(items: Iterable[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Any], ...]]:
    return tuple(
        sorted(
            items,
            key=lambda item: (
                item.get("breach_type", ""),
                item.get("identifier", ""),
            ),
        )
    )


def sort_guard_events(items: Iterable[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Any], ...]]:
    return tuple(sorted(items, key=lambda item: item.get("guard_id", "")))


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
    "concentration_breaches": sort_concentration_breaches,
    "governance_trail": sort_guard_events,
    "guard_results": sort_guard_events,
    "veto_logs": sort_veto_logs,
}
