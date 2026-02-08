from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from typing import Mapping, Sequence

from agentic_system.config.loader import compute_hash
from agentic_system.orchestration.models import RunInputs, RunResult
from agentic_system.penalties import compute_penalties
from agentic_system.schemas.contracts import (
    AgentResult,
    HoldingPacket,
    PortfolioCommitteePacket,
    Scorecard,
)


def _holding_identity_valid(holding) -> bool:
    return bool(holding.instrument.ticker and holding.instrument.exchange and holding.instrument.currency)


def _make_limitation(error_type: str) -> tuple[str, ...]:
    return (error_type,)


def _derive_veto_from_dio(dio_output) -> bool:
    return bool(
        dio_output.missing_hard_stop_fields
        or dio_output.integrity_veto_triggered
        or dio_output.unsourced_numbers_detected
        or any(flag.hard_stop_triggered for flag in dio_output.staleness_flags)
    )


def _risk_officer_veto(risk_output: AgentResult | None) -> bool:
    if not risk_output:
        return False
    return bool(risk_output.veto_flags)


def run_flow(inputs: RunInputs) -> RunResult:
    errors: list[str] = []
    holding_outcomes: dict[str, str] = {}
    holding_packets: list[HoldingPacket] = []

    if not inputs.config.base_currency:
        return RunResult(
            portfolio_outcome="VETOED",
            holding_packets=(),
            committee_packet=None,
            errors=("missing_base_currency",),
        )

    for holding in inputs.snapshot.holdings:
        if not _holding_identity_valid(holding):
            holding_outcomes[holding.holding_id] = "FAILED"
            errors.append(f"identity_validation_error:{holding.holding_id}")
        else:
            holding_outcomes[holding.holding_id] = "COMPLETED"

    grra_output = inputs.portfolio.grra_output
    if grra_output and grra_output.do_not_trade_flag:
        for holding_id in holding_outcomes:
            holding_outcomes[holding_id] = "SHORT_CIRCUITED"
        committee = PortfolioCommitteePacket(
            portfolio_run_outcome="SHORT_CIRCUITED",
            per_holding_outcomes=holding_outcomes,
            holding_packets=(),
            canonical_output_hash=None,
        )
        return RunResult(
            portfolio_outcome="SHORT_CIRCUITED",
            holding_packets=(),
            committee_packet=committee,
            errors=tuple(errors),
        )

    for holding in inputs.snapshot.holdings:
        if holding_outcomes[holding.holding_id] != "COMPLETED":
            continue
        evaluation = inputs.holdings.get(holding.holding_id)
        dio_output = evaluation.dio_output if evaluation else None
        if dio_output and _derive_veto_from_dio(dio_output):
            holding_outcomes[holding.holding_id] = "VETOED"
            errors.append(f"dio_veto:{holding.holding_id}")
            continue

        if _risk_officer_veto(inputs.portfolio.risk_officer_output):
            holding_outcomes[holding.holding_id] = "VETOED"
            errors.append(f"risk_officer_veto:{holding.holding_id}")

    total_holdings = len(holding_outcomes)
    failures = sum(1 for outcome in holding_outcomes.values() if outcome in {"FAILED", "VETOED"})
    failure_rate_pct = (failures / total_holdings) * 100 if total_holdings else 0.0
    portfolio_outcome = "COMPLETED"
    if failure_rate_pct > inputs.run_config.partial_failure_veto_threshold_pct:
        portfolio_outcome = "VETOED"

    penalties_by_holding = defaultdict(lambda: None)
    if portfolio_outcome == "COMPLETED":
        for holding in inputs.snapshot.holdings:
            if holding_outcomes[holding.holding_id] != "COMPLETED":
                continue
            evaluation = inputs.holdings.get(holding.holding_id)
            if not evaluation or not evaluation.dio_output:
                continue
            penalties = compute_penalties(
                holding_id=holding.holding_id,
                dio_output=evaluation.dio_output,
                agent_results=evaluation.agent_results,
                run_config=inputs.run_config,
                fx_flags=(),
            )
            penalties_by_holding[holding.holding_id] = penalties

    for holding in inputs.snapshot.holdings:
        outcome = holding_outcomes[holding.holding_id]
        if outcome in {"FAILED", "VETOED", "SHORT_CIRCUITED"}:
            holding_packets.append(
                HoldingPacket(
                    holding_id=holding.holding_id,
                    instrument=holding.instrument,
                    holding_run_outcome=outcome,
                    limitations=_make_limitation(outcome.lower()),
                )
            )
            continue
        penalties = penalties_by_holding.get(holding.holding_id)
        scorecard = None
        if penalties:
            base_score = 100.0
            final_score = max(0.0, base_score + penalties.breakdown.total_penalties)
            scorecard = Scorecard(
                base_score=base_score,
                penalty_breakdown=penalties.breakdown,
                final_score=final_score,
            )
        holding_packets.append(
            HoldingPacket(
                holding_id=holding.holding_id,
                instrument=holding.instrument,
                holding_run_outcome=outcome,
                scorecard=scorecard,
            )
        )

    committee_packet = None
    if portfolio_outcome in {"COMPLETED", "SHORT_CIRCUITED"}:
        committee_packet = PortfolioCommitteePacket(
            portfolio_run_outcome=portfolio_outcome,
            per_holding_outcomes=holding_outcomes,
            holding_packets=tuple(holding_packets),
            canonical_output_hash=None,
        )
        if portfolio_outcome == "COMPLETED":
            committee_packet = replace(
                committee_packet,
                canonical_output_hash=compute_hash(committee_packet),
            )

    return RunResult(
        portfolio_outcome=portfolio_outcome,
        holding_packets=tuple(holding_packets),
        committee_packet=committee_packet,
        errors=tuple(errors),
    )
