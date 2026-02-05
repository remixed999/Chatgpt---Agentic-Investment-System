from __future__ import annotations

from src.core.models import AgentResult, ConfigSnapshot, PortfolioConfig, RunConfig, RunMode
from src.core.penalties import (
    ContradictionRecord,
    CorporateActionRisk,
    DIOOutput,
    MissingField,
    StalenessFlag,
)
from src.core.penalties.penalty_engine import compute_penalty_breakdown


def _base_run_config(run_mode: RunMode = RunMode.FAST) -> RunConfig:
    return RunConfig(run_mode=run_mode)


def _base_config_snapshot() -> ConfigSnapshot:
    return ConfigSnapshot(rubric_version="v0", registries={}, hash="hash")


def _base_portfolio_config() -> PortfolioConfig:
    return PortfolioConfig(base_currency="USD")


def test_hard_stop_veto_returns_zero_penalties():
    breakdown = compute_penalty_breakdown(
        holding_id="H1",
        run_config=_base_run_config(),
        config_snapshot=_base_config_snapshot(),
        dio_output=DIOOutput(missing_hard_stop_fields=["cash"]),
        agent_results=[],
        portfolio_config=_base_portfolio_config(),
    )

    assert breakdown.total_penalties == 0.0
    assert breakdown.details == []


def test_missing_cash_or_runway_penalizes_non_burn_rate_company():
    breakdown = compute_penalty_breakdown(
        holding_id="H1",
        run_config=_base_run_config(),
        config_snapshot=_base_config_snapshot(),
        dio_output=DIOOutput(missing_penalty_critical_fields=[MissingField(field_name="cash")]),
        agent_results=[],
        portfolio_config=_base_portfolio_config(),
    )

    assert breakdown.category_A_missing_critical == -6.0
    assert any(item.reason == "missing_cash_or_runway" for item in breakdown.details)


def test_not_applicable_missing_cash_does_not_penalize():
    breakdown = compute_penalty_breakdown(
        holding_id="H1",
        run_config=_base_run_config(),
        config_snapshot=_base_config_snapshot(),
        dio_output=DIOOutput(missing_penalty_critical_fields=[MissingField(field_name="cash", not_applicable=True)]),
        agent_results=[],
        portfolio_config=_base_portfolio_config(),
    )

    assert breakdown.category_A_missing_critical == 0.0
    assert breakdown.details == []


def test_staleness_penalty_within_threshold_and_hard_stop_veto():
    penalty_breakdown = compute_penalty_breakdown(
        holding_id="H1",
        run_config=_base_run_config(run_mode=RunMode.FAST),
        config_snapshot=_base_config_snapshot(),
        dio_output=DIOOutput(
            staleness_flags=[StalenessFlag(staleness_type="financials", age_days=130, hard_stop_triggered=False)],
        ),
        agent_results=[],
        portfolio_config=_base_portfolio_config(),
    )

    assert penalty_breakdown.category_B_staleness == -5.0

    veto_breakdown = compute_penalty_breakdown(
        holding_id="H1",
        run_config=_base_run_config(run_mode=RunMode.FAST),
        config_snapshot=_base_config_snapshot(),
        dio_output=DIOOutput(
            staleness_flags=[StalenessFlag(staleness_type="financials", age_days=500, hard_stop_triggered=True)],
        ),
        agent_results=[],
        portfolio_config=_base_portfolio_config(),
    )

    assert veto_breakdown.total_penalties == 0.0
    assert veto_breakdown.details == []


def test_corporate_action_split_applies_category_f_only():
    breakdown = compute_penalty_breakdown(
        holding_id="H1",
        run_config=_base_run_config(),
        config_snapshot=_base_config_snapshot(),
        dio_output=DIOOutput(corporate_action_risk=CorporateActionRisk(split_days_ago=60)),
        agent_results=[],
        portfolio_config=_base_portfolio_config(),
    )

    assert breakdown.category_F_data_validity == -6.0
    assert breakdown.category_B_staleness == 0.0


def test_total_cap_enforcement_drops_deterministic_items():
    dio_output = DIOOutput(
        missing_penalty_critical_fields=[
            MissingField(field_name="cash"),
            MissingField(field_name="price"),
        ],
        staleness_flags=[
            StalenessFlag(staleness_type="financials", age_days=200),
            StalenessFlag(staleness_type="price_volume", age_days=10),
            StalenessFlag(staleness_type="company_updates", age_days=100),
        ],
        contradictions=[ContradictionRecord(unresolved=False)],
        corporate_action_risk=CorporateActionRisk(split_days_ago=30, dividend_days_ago=45),
    )
    agent_results = [
        AgentResult(
            agent_name="FundamentalsAgent",
            scope="holding",
            status="completed",
            holding_id="H1",
            confidence=0.2,
        ),
        AgentResult(
            agent_name="TechnicalAgent",
            scope="holding",
            status="completed",
            holding_id="H1",
            confidence=0.3,
        ),
        AgentResult(
            agent_name="MacroAgent",
            scope="holding",
            status="completed",
            holding_id="H1",
            confidence=0.4,
        ),
    ]

    breakdown = compute_penalty_breakdown(
        holding_id="H1",
        run_config=_base_run_config(run_mode=RunMode.DEEP),
        config_snapshot=_base_config_snapshot(),
        dio_output=dio_output,
        agent_results=agent_results,
        portfolio_config=_base_portfolio_config(),
    )

    reasons = {item.reason for item in breakdown.details}
    assert breakdown.total_penalties == -35.0
    assert "stale_company_updates" not in reasons
    assert "recent_dividend_or_distribution" not in reasons
    assert breakdown.category_B_staleness == -8.0
    assert breakdown.category_F_data_validity == -6.0


def test_deterministic_detail_ordering():
    dio_output_a = DIOOutput(
        missing_penalty_critical_fields=[
            MissingField(field_name="price"),
            MissingField(field_name="cash"),
        ],
        contradictions=[ContradictionRecord(unresolved=True)],
    )
    dio_output_b = DIOOutput(
        missing_penalty_critical_fields=[
            MissingField(field_name="cash"),
            MissingField(field_name="price"),
        ],
        contradictions=[ContradictionRecord(unresolved=True)],
    )

    breakdown_a = compute_penalty_breakdown(
        holding_id="H1",
        run_config=_base_run_config(run_mode=RunMode.DEEP),
        config_snapshot=_base_config_snapshot(),
        dio_output=dio_output_a,
        agent_results=[],
        portfolio_config=_base_portfolio_config(),
    )
    breakdown_b = compute_penalty_breakdown(
        holding_id="H1",
        run_config=_base_run_config(run_mode=RunMode.DEEP),
        config_snapshot=_base_config_snapshot(),
        dio_output=dio_output_b,
        agent_results=[],
        portfolio_config=_base_portfolio_config(),
    )

    assert breakdown_a.details == breakdown_b.details
    assert breakdown_a.total_penalties == breakdown_b.total_penalties
