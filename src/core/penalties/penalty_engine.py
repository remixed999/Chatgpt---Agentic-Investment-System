from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

from src.core.models import AgentResult, ConfigSnapshot, PenaltyBreakdown, PenaltyItem, PortfolioConfig, RunConfig, RunMode
from src.core.penalties.models import DIOOutput, FXExposureReport, MissingField


@dataclass(frozen=True)
class _Thresholds:
    stale_financials: float
    stale_price_volume: float
    stale_company_updates: float
    stale_macro_regime: float


DEFAULT_THRESHOLDS = {
    RunMode.FAST: _Thresholds(
        stale_financials=120.0,
        stale_price_volume=3.0,
        stale_company_updates=90.0,
        stale_macro_regime=14.0,
    ),
    RunMode.DEEP: _Thresholds(
        stale_financials=90.0,
        stale_price_volume=1.0,
        stale_company_updates=60.0,
        stale_macro_regime=7.0,
    ),
}

CATEGORY_CAPS = {
    "A": -20.0,
    "B": -10.0,
    "C": -20.0,
    "D": -10.0,
    "E": -10.0,
    "F": -10.0,
}

TOTAL_CAPS = {
    RunMode.DEEP: -35.0,
    RunMode.FAST: -40.0,
}


def compute_penalty_breakdown(
    holding_id: str,
    run_config: RunConfig,
    config_snapshot: ConfigSnapshot,
    dio_output: DIOOutput,
    agent_results: Sequence[AgentResult],
    portfolio_config: PortfolioConfig,
    pscc_output_optional: Optional[FXExposureReport] = None,
) -> PenaltyBreakdown:
    if _dio_hard_stop_triggered(dio_output):
        return _zero_breakdown()

    items: List[PenaltyItem] = []
    is_burn_rate_company = bool(run_config.burn_rate_classification.get(holding_id))
    missing_fields = _normalize_missing_fields(dio_output.missing_penalty_critical_fields)

    for missing in missing_fields:
        if missing.not_applicable:
            continue
        field_name = missing.field_name
        if field_name in {"cash", "runway_months", "burn_rate"}:
            if not is_burn_rate_company:
                items.append(_item("A", "missing_cash_or_runway", -6.0, "DIO"))
            continue
        if field_name in {"shares_outstanding", "market_cap"}:
            items.append(_item("A", "missing_shares_or_market_cap", -5.0, "DIO"))
            continue
        if field_name == "fully_diluted_shares":
            items.append(_item("A", "missing_fully_diluted_shares", -4.0, "DIO"))
            continue
        if field_name in {"adv_usd", "liquidity_measure"}:
            items.append(_item("A", "missing_liquidity_measure", -5.0, "DIO"))
            continue
        if field_name in {"price", "volume"}:
            items.append(_item("A", "missing_price_or_volume", -4.0, "DIO"))
            continue
        if field_name in {"macro_regime_input", "vix", "macro_regime"}:
            items.append(_item("A", "missing_macro_regime_input", -4.0, "DIO"))
            continue

    thresholds = _resolve_thresholds(run_config)
    for flag in dio_output.staleness_flags:
        if flag.hard_stop_triggered:
            continue
        reason = _staleness_reason(flag.staleness_type)
        if reason is None:
            continue
        limit = getattr(thresholds, reason)
        if flag.age_days > limit:
            items.append(_item("B", reason, _staleness_amount(reason), "DIO"))

    if dio_output.contradictions:
        items.append(_item("C", "contradiction_detected", -10.0, "DIO"))
        if any(record.unresolved for record in dio_output.contradictions):
            items.append(_item("C", "conflict_unresolved", -6.0, "DIO"))
    if dio_output.unsourced_numbers_detected:
        items.append(_item("C", "unsourced_numbers_detected", -10.0, "DIO"))

    if _count_low_confidence(agent_results, holding_id) >= 3:
        items.append(_item("D", "low_confidence_multi_agent", -5.0, "PenaltyEngine"))
    if _devils_advocate_unresolved(agent_results, holding_id):
        items.append(_item("D", "devils_advocate_unresolved_fatal_risk", -5.0, "DevilsAdvocate"))

    items.extend(_fx_items(portfolio_config, pscc_output_optional))

    items.extend(_data_validity_items(dio_output))

    items = _dedupe_items(items)
    items = _apply_category_caps(items, _resolve_category_caps(run_config))
    items = _apply_total_cap(items, _resolve_total_cap(run_config))

    return _build_breakdown(items)


def _dio_hard_stop_triggered(dio_output: DIOOutput) -> bool:
    if dio_output.integrity_veto_triggered:
        return True
    if dio_output.missing_hard_stop_fields:
        return True
    if any(flag.hard_stop_triggered for flag in dio_output.staleness_flags):
        return True
    return False


def _zero_breakdown() -> PenaltyBreakdown:
    return PenaltyBreakdown(
        category_A_missing_critical=0.0,
        category_B_staleness=0.0,
        category_C_contradictions_integrity=0.0,
        category_D_confidence=0.0,
        category_E_fx_exposure_risk=0.0,
        category_F_data_validity=0.0,
        total_penalties=0.0,
        details=[],
    )


def _item(category: str, reason: str, amount: float, source_agent: str) -> PenaltyItem:
    return PenaltyItem(category=category, reason=reason, amount=amount, source_agent=source_agent)


def _normalize_missing_fields(entries: Iterable[MissingField | str]) -> List[MissingField]:
    normalized = []
    for entry in entries:
        if isinstance(entry, MissingField):
            normalized.append(entry)
        else:
            normalized.append(MissingField(field_name=str(entry), not_applicable=False))
    return normalized


def _resolve_thresholds(run_config: RunConfig) -> _Thresholds:
    defaults = DEFAULT_THRESHOLDS[run_config.run_mode]
    thresholds = run_config.staleness_thresholds or {}
    if isinstance(thresholds.get(run_config.run_mode.value), dict):
        thresholds = thresholds[run_config.run_mode.value]
    return _Thresholds(
        stale_financials=thresholds.get("stale_financials", defaults.stale_financials),
        stale_price_volume=thresholds.get("stale_price_volume", defaults.stale_price_volume),
        stale_company_updates=thresholds.get("stale_company_updates", defaults.stale_company_updates),
        stale_macro_regime=thresholds.get("stale_macro_regime", defaults.stale_macro_regime),
    )


def _resolve_category_caps(run_config: RunConfig) -> Dict[str, float]:
    caps = CATEGORY_CAPS.copy()
    for key, value in (run_config.penalty_caps or {}).items():
        if key in caps:
            caps[key] = float(value)
    return caps


def _resolve_total_cap(run_config: RunConfig) -> float:
    caps = run_config.penalty_caps or {}
    if "total" in caps:
        return float(caps["total"])
    return TOTAL_CAPS[run_config.run_mode]


def _staleness_reason(staleness_type: str) -> Optional[str]:
    mapping = {
        "financials": "stale_financials",
        "price_volume": "stale_price_volume",
        "company_updates": "stale_company_updates",
        "macro_regime": "stale_macro_regime",
    }
    return mapping.get(staleness_type)


def _staleness_amount(reason: str) -> float:
    amounts = {
        "stale_financials": -5.0,
        "stale_price_volume": -3.0,
        "stale_company_updates": -2.0,
        "stale_macro_regime": -4.0,
    }
    return amounts[reason]


def _count_low_confidence(agent_results: Sequence[AgentResult], holding_id: str) -> int:
    count = 0
    for agent in agent_results:
        if agent.scope != "holding" or agent.holding_id != holding_id:
            continue
        if agent.confidence is not None and agent.confidence < 0.5:
            count += 1
    return count


def _devils_advocate_unresolved(agent_results: Sequence[AgentResult], holding_id: str) -> bool:
    for agent in agent_results:
        if agent.scope != "holding" or agent.holding_id != holding_id:
            continue
        if "devil" not in agent.agent_name.lower():
            continue
        findings = agent.key_findings or {}
        if findings.get("unresolved_fatal_risk") or findings.get("fatal_risk_unresolved"):
            return True
    return False


def _fx_items(
    portfolio_config: PortfolioConfig,
    pscc_output_optional: Optional[FXExposureReport],
) -> List[PenaltyItem]:
    if pscc_output_optional is None:
        return []
    if pscc_output_optional.fx_hard_stop_triggered:
        return []
    base_currency = portfolio_config.base_currency
    holding_currency = pscc_output_optional.holding_currency
    if not base_currency or not holding_currency or base_currency == holding_currency:
        return []
    items: List[PenaltyItem] = []
    if pscc_output_optional.fx_rate_missing:
        items.append(_item("E", "fx_rate_missing", -5.0, "PSCC"))
    if pscc_output_optional.fx_rate_stale:
        items.append(_item("E", "fx_rate_stale", -3.0, "PSCC"))
    if (
        pscc_output_optional.fx_exposure_pct is not None
        and pscc_output_optional.fx_exposure_pct > 0.2
        and pscc_output_optional.hedge_data_missing
    ):
        items.append(_item("E", "fx_exposure_high_no_hedge_data", -5.0, "PSCC"))
    return items


def _data_validity_items(dio_output: DIOOutput) -> List[PenaltyItem]:
    items: List[PenaltyItem] = []
    risk = dio_output.corporate_action_risk
    if risk:
        if risk.split_days_ago is not None and risk.split_days_ago <= 90:
            items.append(_item("F", "recent_split_or_reverse_split", -6.0, "DIO"))
        if risk.dividend_days_ago is not None and risk.dividend_days_ago <= 90:
            items.append(_item("F", "recent_dividend_or_distribution", -3.0, "DIO"))
        if risk.spinoff_or_merger_days_ago is not None and risk.spinoff_or_merger_days_ago <= 180:
            items.append(_item("F", "recent_spinoff_or_merger", -8.0, "DIO"))
    if dio_output.low_source_reliability:
        items.append(_item("F", "low_source_reliability", -5.0, "DIO"))
    return items


def _dedupe_items(items: Iterable[PenaltyItem]) -> List[PenaltyItem]:
    deduped: Dict[tuple[str, str, str], PenaltyItem] = {}
    for item in items:
        key = (item.category, item.reason, item.source_agent)
        if key not in deduped:
            deduped[key] = item
    return list(deduped.values())


def _apply_category_caps(items: List[PenaltyItem], caps: Dict[str, float]) -> List[PenaltyItem]:
    by_category: Dict[str, List[PenaltyItem]] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)
    trimmed: List[PenaltyItem] = []
    for category, category_items in by_category.items():
        cap = caps.get(category)
        if cap is None:
            trimmed.extend(category_items)
            continue
        trimmed.extend(_drop_items_to_cap(category_items, cap, _category_drop_order))
    return trimmed


def _apply_total_cap(items: List[PenaltyItem], total_cap: float) -> List[PenaltyItem]:
    total = sum(item.amount for item in items)
    if total >= total_cap:
        return items
    remaining = _drop_items_to_cap(items, total_cap, _total_drop_order)
    return remaining


def _drop_items_to_cap(
    items: List[PenaltyItem],
    cap: float,
    drop_order: callable,
) -> List[PenaltyItem]:
    total = sum(item.amount for item in items)
    if total >= cap:
        return items
    ordered = drop_order(items)
    remaining = list(items)
    for item in ordered:
        if total >= cap:
            break
        total -= item.amount
        if item in remaining:
            remaining.remove(item)
    return remaining


def _category_drop_order(items: List[PenaltyItem]) -> List[PenaltyItem]:
    ordered = sorted(items, key=lambda item: item.reason, reverse=True)
    ordered = sorted(ordered, key=lambda item: abs(item.amount))
    return ordered


def _total_drop_order(items: List[PenaltyItem]) -> List[PenaltyItem]:
    category_rank = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
    ordered = sorted(items, key=lambda item: item.reason, reverse=True)
    ordered = sorted(ordered, key=lambda item: category_rank.get(item.category, 0), reverse=True)
    ordered = sorted(ordered, key=lambda item: abs(item.amount))
    return ordered


def _build_breakdown(items: List[PenaltyItem]) -> PenaltyBreakdown:
    totals = {category: 0.0 for category in CATEGORY_CAPS}
    for item in items:
        totals[item.category] += item.amount
    details = sorted(
        items,
        key=lambda item: (item.category, item.reason, item.source_agent),
    )
    total_penalties = sum(totals.values())
    return PenaltyBreakdown(
        category_A_missing_critical=totals["A"],
        category_B_staleness=totals["B"],
        category_C_contradictions_integrity=totals["C"],
        category_D_confidence=totals["D"],
        category_E_fx_exposure_risk=totals["E"],
        category_F_data_validity=totals["F"],
        total_penalties=total_penalties,
        details=details,
    )
