from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from agentic_system.schemas.contracts import (
    AgentResult,
    DIOOutput,
    PenaltyBreakdown,
    PenaltyItem,
    RunConfig,
)


@dataclass(frozen=True)
class PenaltyComputation:
    breakdown: PenaltyBreakdown
    items: tuple[PenaltyItem, ...]


_CATEGORY_CAPS = {
    "A": -20.0,
    "B": -10.0,
    "C": -20.0,
    "D": -10.0,
    "E": -10.0,
    "F": -10.0,
}


_REASON_MAP = {
    "missing_cash_or_runway": -6.0,
    "missing_shares_or_market_cap": -5.0,
    "missing_fully_diluted_shares": -4.0,
    "missing_liquidity_measure": -5.0,
    "missing_price_or_volume": -4.0,
    "missing_macro_regime_input": -4.0,
    "stale_financials": -5.0,
    "stale_price_volume": -3.0,
    "stale_company_updates": -2.0,
    "stale_macro_regime": -4.0,
    "contradiction_detected": -10.0,
    "conflict_unresolved": -6.0,
    "unsourced_numbers_detected": -10.0,
    "low_confidence_multi_agent": -5.0,
    "devils_advocate_unresolved_fatal_risk": -5.0,
    "fx_rate_missing": -5.0,
    "fx_rate_stale": -3.0,
    "fx_exposure_high_no_hedge_data": -5.0,
    "recent_split_or_reverse_split": -6.0,
    "recent_dividend_or_distribution": -3.0,
    "recent_spinoff_or_merger": -8.0,
    "low_source_reliability": -5.0,
}


def _make_item(category: str, reason: str, source_agent: str) -> PenaltyItem:
    amount = _REASON_MAP[reason]
    return PenaltyItem(category=category, reason=reason, amount=amount, source_agent=source_agent)


def _dedupe(items: Iterable[PenaltyItem]) -> list[PenaltyItem]:
    seen = set()
    unique: list[PenaltyItem] = []
    for item in items:
        key = (item.category, item.reason, item.source_agent)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _sort_items(items: Sequence[PenaltyItem]) -> list[PenaltyItem]:
    return sorted(items, key=lambda item: (item.category, item.reason, item.source_agent))


def _apply_category_caps(items: list[PenaltyItem]) -> list[PenaltyItem]:
    capped: list[PenaltyItem] = []
    for category in sorted(_CATEGORY_CAPS.keys()):
        category_items = [item for item in items if item.category == category]
        category_items.sort(key=lambda item: (item.amount, item.reason))
        total = 0.0
        for item in category_items:
            if total + item.amount < _CATEGORY_CAPS[category]:
                continue
            total += item.amount
            capped.append(item)
    return capped


def _apply_total_cap(items: list[PenaltyItem], total_cap: float) -> list[PenaltyItem]:
    total = sum(item.amount for item in items)
    if total >= total_cap:
        return items
    ordered = sorted(
        items,
        key=lambda item: (
            abs(item.amount),
            -ord(item.category),
            item.reason,
            item.source_agent,
        ),
    )
    while ordered and total < total_cap:
        removed = ordered.pop(0)
        total -= removed.amount
    return ordered


def _category_totals(items: Sequence[PenaltyItem]) -> Mapping[str, float]:
    totals = {key: 0.0 for key in _CATEGORY_CAPS.keys()}
    for item in items:
        totals[item.category] += item.amount
    return totals


def compute_penalties(
    holding_id: str,
    dio_output: DIOOutput,
    agent_results: Sequence[AgentResult],
    run_config: RunConfig,
    fx_flags: Sequence[str],
) -> PenaltyComputation:
    if (
        dio_output.missing_hard_stop_fields
        or dio_output.integrity_veto_triggered
        or dio_output.unsourced_numbers_detected
    ):
        empty = PenaltyBreakdown(
            category_A_missing_critical=0.0,
            category_B_staleness=0.0,
            category_C_contradictions_integrity=0.0,
            category_D_confidence=0.0,
            category_E_fx_exposure_risk=0.0,
            category_F_data_validity=0.0,
            total_penalties=0.0,
            details=(),
        )
        return PenaltyComputation(breakdown=empty, items=())

    items: list[PenaltyItem] = []

    missing_fields = set(dio_output.missing_penalty_critical_fields)
    burn_rate = run_config.burn_rate_classification.get(holding_id)
    if burn_rate and burn_rate.is_burn_rate_company:
        missing_fields -= {"cash", "runway_months", "burn_rate"}
    if {"cash", "runway_months"} & missing_fields:
        items.append(_make_item("A", "missing_cash_or_runway", dio_output.agent_name))
    if {"shares_outstanding", "market_cap"} & missing_fields:
        items.append(_make_item("A", "missing_shares_or_market_cap", dio_output.agent_name))
    if "fully_diluted_shares" in missing_fields:
        items.append(_make_item("A", "missing_fully_diluted_shares", dio_output.agent_name))
    if {"adv_usd", "bid_ask_spread_bps"} & missing_fields:
        items.append(_make_item("A", "missing_liquidity_measure", dio_output.agent_name))
    if {"price", "volume"} & missing_fields:
        items.append(_make_item("A", "missing_price_or_volume", dio_output.agent_name))
    if {"vix", "credit_spreads", "market_breadth"} & missing_fields:
        items.append(_make_item("A", "missing_macro_regime_input", dio_output.agent_name))

    for flag in dio_output.staleness_flags:
        if flag.hard_stop_triggered or not flag.penalty_triggered:
            continue
        if flag.data_category == "financials":
            items.append(_make_item("B", "stale_financials", dio_output.agent_name))
        if flag.data_category == "price_volume":
            items.append(_make_item("B", "stale_price_volume", dio_output.agent_name))
        if flag.data_category == "company_updates":
            items.append(_make_item("B", "stale_company_updates", dio_output.agent_name))
        if flag.data_category == "macro_regime":
            items.append(_make_item("B", "stale_macro_regime", dio_output.agent_name))

    if dio_output.contradictions:
        items.append(_make_item("C", "contradiction_detected", dio_output.agent_name))
    if "unresolved_conflict" in dio_output.contradictions:
        items.append(_make_item("C", "conflict_unresolved", dio_output.agent_name))
    if dio_output.unsourced_numbers_detected:
        items.append(_make_item("C", "unsourced_numbers_detected", dio_output.agent_name))

    low_confidence = sum(1 for agent in agent_results if agent.confidence < 0.5)
    if low_confidence >= 3:
        items.append(_make_item("D", "low_confidence_multi_agent", "RiskOfficer"))
    for agent in agent_results:
        if agent.agent_name.lower().startswith("devil") and agent.key_findings.get(
            "unresolved_fatal_risk"
        ):
            items.append(
                _make_item("D", "devils_advocate_unresolved_fatal_risk", agent.agent_name)
            )

    if "fx_rate_missing" in fx_flags:
        items.append(_make_item("E", "fx_rate_missing", "PSCC"))
    if "fx_rate_stale" in fx_flags:
        items.append(_make_item("E", "fx_rate_stale", "PSCC"))
    if "fx_exposure_high_no_hedge_data" in fx_flags:
        items.append(_make_item("E", "fx_exposure_high_no_hedge_data", "PSCC"))

    if "recent_split_or_reverse_split" in dio_output.corporate_action_risk:
        items.append(_make_item("F", "recent_split_or_reverse_split", dio_output.agent_name))
    if "recent_dividend_or_distribution" in dio_output.corporate_action_risk:
        items.append(_make_item("F", "recent_dividend_or_distribution", dio_output.agent_name))
    if "recent_spinoff_or_merger" in dio_output.corporate_action_risk:
        items.append(_make_item("F", "recent_spinoff_or_merger", dio_output.agent_name))
    if "low_source_reliability" in dio_output.corporate_action_risk:
        items.append(_make_item("F", "low_source_reliability", dio_output.agent_name))

    unique_items = _dedupe(items)
    capped_items = _apply_category_caps(unique_items)
    total_cap = run_config.penalty_caps.total_penalty_cap
    capped_items = _apply_total_cap(capped_items, total_cap)
    ordered_items = _sort_items(capped_items)
    totals = _category_totals(ordered_items)
    breakdown = PenaltyBreakdown(
        category_A_missing_critical=totals["A"],
        category_B_staleness=totals["B"],
        category_C_contradictions_integrity=totals["C"],
        category_D_confidence=totals["D"],
        category_E_fx_exposure_risk=totals["E"],
        category_F_data_validity=totals["F"],
        total_penalties=sum(totals.values()),
        details=tuple(ordered_items),
    )
    return PenaltyComputation(breakdown=breakdown, items=tuple(ordered_items))

