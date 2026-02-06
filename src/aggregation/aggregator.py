from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

from pydantic import ValidationError

from src.aggregation.caps import apply_lefo_caps, apply_pscc_caps
from src.aggregation.scoring import compute_base_score
from src.core.canonicalization.hashing import compute_run_hashes
from src.core.models import (
    AgentResult,
    FailedRunPacket,
    GuardResult,
    HoldingInput,
    HoldingPacket,
    PenaltyBreakdown,
    PortfolioCommitteePacket,
    PortfolioConfig,
    PortfolioSnapshot,
    RunConfig,
    RunOutcome,
    Scorecard,
)
from src.core.penalties import DIOOutput, FXExposureReport, compute_penalty_breakdown_with_cap_tracking


@dataclass
class HoldingState:
    holding: HoldingInput
    outcome: RunOutcome
    reasons: List[str]


def build_holding_packet(
    holding_ctx: HoldingInput,
    agent_results: Sequence[AgentResult],
    penalties: Optional[Scorecard],
    lefo: Optional[Dict[str, Any]],
    pscc: Optional[Dict[str, Any]],
    governance_outcome: RunOutcome,
    reasons: Optional[List[str]] = None,
) -> HoldingPacket:
    holding_id = holding_ctx.identity.holding_id if holding_ctx.identity else None
    limitations = list(reasons or [])

    if governance_outcome != RunOutcome.COMPLETED:
        if governance_outcome == RunOutcome.FAILED:
            limitations = [f"error_classification:{reason}" for reason in limitations] or limitations
        scorecard = Scorecard(penalty_breakdown=_zero_breakdown())
        return HoldingPacket(
            holding_id=holding_id,
            identity=holding_ctx.identity,
            holding_run_outcome=governance_outcome,
            scorecard=scorecard,
            limitations=limitations,
        )

    scorecard = penalties or Scorecard()
    scorecard = apply_lefo_caps(scorecard, lefo)
    scorecard = apply_pscc_caps(scorecard, pscc, holding_id)

    if scorecard.base_score is not None and scorecard.penalty_breakdown is not None:
        final_score = scorecard.base_score + scorecard.penalty_breakdown.total_penalties
        scorecard.final_score = _clamp_score(final_score)

    return HoldingPacket(
        holding_id=holding_id,
        identity=holding_ctx.identity,
        holding_run_outcome=governance_outcome,
        scorecard=scorecard,
        limitations=limitations,
    )


def build_portfolio_packet(
    *,
    run_id: str,
    portfolio_snapshot: PortfolioSnapshot,
    portfolio_config: PortfolioConfig,
    run_config: RunConfig,
    config_snapshot: Any,
    outcome: RunOutcome,
    reasons: List[str],
    holding_states: Iterable[HoldingState],
    agent_results: Sequence[AgentResult],
    guard_results: Iterable[GuardResult],
) -> PortfolioCommitteePacket | FailedRunPacket:
    if outcome == RunOutcome.FAILED:
        return FailedRunPacket(
            run_id=run_id,
            portfolio_run_outcome=RunOutcome.FAILED,
            failure_reason=reasons[0] if reasons else "unknown_failure",
            reasons=reasons,
            portfolio_id=portfolio_snapshot.portfolio_id,
            as_of_date=portfolio_snapshot.as_of_date,
            base_currency=portfolio_config.base_currency,
            run_mode=run_config.run_mode,
        )

    indexed_states = list(enumerate(holding_states))
    ordered_states = sorted(
        indexed_states,
        key=lambda item: (
            item[1].holding.identity.holding_id if item[1].holding.identity else "",
            item[0],
        ),
    )
    holdings_packets: List[HoldingPacket] = []
    per_holding_outcomes: Dict[str, str] = {}

    pscc_output = _extract_pscc_portfolio_output(agent_results)

    for index, state in ordered_states:
        holding = state.holding
        holding_id = holding.identity.holding_id if holding.identity else ""
        if not holding_id:
            holding_id = f"holding_index_{index}"
        per_holding_outcomes[holding_id] = state.outcome.value
        if outcome == RunOutcome.VETOED:
            continue

        if outcome == RunOutcome.SHORT_CIRCUITED:
            packet = build_holding_packet(
                holding_ctx=holding,
                agent_results=agent_results,
                penalties=None,
                lefo=None,
                pscc=None,
                governance_outcome=RunOutcome.SHORT_CIRCUITED,
                reasons=state.reasons,
            )
            holdings_packets.append(packet)
            continue

        if state.outcome != RunOutcome.COMPLETED:
            packet = build_holding_packet(
                holding_ctx=holding,
                agent_results=agent_results,
                penalties=None,
                lefo=None,
                pscc=None,
                governance_outcome=state.outcome,
                reasons=state.reasons,
            )
            holdings_packets.append(packet)
            continue

        penalties = _build_scorecard(
            holding_ctx=holding,
            agent_results=agent_results,
            run_config=run_config,
            config_snapshot=config_snapshot,
            portfolio_config=portfolio_config,
        )
        lefo_output = _extract_lefo_output(agent_results, holding_id)
        packet = build_holding_packet(
            holding_ctx=holding,
            agent_results=agent_results,
            penalties=penalties,
            lefo=lefo_output,
            pscc=pscc_output,
            governance_outcome=state.outcome,
            reasons=state.reasons,
        )
        holdings_packets.append(packet)

    summary = _build_summary(outcome, reasons, [state for _, state in ordered_states])
    governance_trail = [guard.model_dump() for guard in sorted(guard_results, key=lambda guard: guard.guard_id)]

    portfolio_packet = PortfolioCommitteePacket(
        run_id=run_id,
        portfolio_id=portfolio_snapshot.portfolio_id,
        portfolio_run_outcome=outcome,
        holdings=holdings_packets,
        per_holding_outcomes=per_holding_outcomes,
        summary=summary,
        governance_trail=governance_trail,
        agent_outputs=_sorted_agent_outputs(agent_results),
    )

    if outcome == RunOutcome.COMPLETED:
        decision_payload = {
            "portfolio_committee_packet": portfolio_packet,
            "holding_packets": holdings_packets,
        }
        hashes = compute_run_hashes(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            committee_packet=portfolio_packet,
            decision_payload=decision_payload,
        )
        portfolio_packet.snapshot_hash = hashes.snapshot_hash
        portfolio_packet.config_hash = hashes.config_hash
        portfolio_packet.run_config_hash = hashes.run_config_hash
        portfolio_packet.decision_hash = hashes.decision_hash
        portfolio_packet.run_hash = hashes.run_hash

    return portfolio_packet


def _build_scorecard(
    *,
    holding_ctx: HoldingInput,
    agent_results: Sequence[AgentResult],
    run_config: RunConfig,
    config_snapshot: Any,
    portfolio_config: PortfolioConfig,
) -> Scorecard:
    holding_id = holding_ctx.identity.holding_id if holding_ctx.identity else ""
    rubric = getattr(config_snapshot, "registries", {}).get("scoring_rubric")
    base_score = compute_base_score(holding_ctx, rubric, agent_results)
    dio_output = _extract_dio_output(agent_results, holding_id)
    fx_report = _extract_fx_report(agent_results, holding_id)
    penalty_breakdown, cap_applied = compute_penalty_breakdown_with_cap_tracking(
        holding_id=holding_id,
        run_config=run_config,
        config_snapshot=config_snapshot,
        dio_output=dio_output,
        agent_results=agent_results,
        portfolio_config=portfolio_config,
        pscc_output_optional=fx_report,
    )
    scorecard = Scorecard(base_score=base_score, penalty_breakdown=penalty_breakdown)
    if cap_applied:
        scorecard.notes.append("penalty_cap_applied")
    return scorecard


def _extract_dio_output(agent_results: Sequence[AgentResult], holding_id: str) -> DIOOutput:
    for agent in agent_results:
        if agent.agent_name != "DIO":
            continue
        if agent.scope != "holding" or agent.holding_id != holding_id:
            continue
        try:
            return DIOOutput.parse_obj(agent.key_findings)
        except ValidationError:
            return DIOOutput()
    return DIOOutput()


def _extract_fx_report(agent_results: Sequence[AgentResult], holding_id: str) -> Optional[FXExposureReport]:
    for agent in agent_results:
        if agent.agent_name != "PSCC":
            continue
        if agent.scope == "holding" and agent.holding_id == holding_id:
            payload = agent.key_findings.get("fx_exposure_report")
            if payload is None:
                continue
            try:
                return FXExposureReport.parse_obj(payload)
            except ValidationError:
                return None
        if agent.scope == "portfolio":
            payload = agent.key_findings.get("fx_exposure_reports", {}).get(holding_id)
            if payload is None:
                continue
            try:
                return FXExposureReport.parse_obj(payload)
            except ValidationError:
                return None
    return None


def _extract_lefo_output(agent_results: Sequence[AgentResult], holding_id: str) -> Optional[Dict[str, Any]]:
    for agent in agent_results:
        if agent.agent_name != "LEFO" or agent.scope != "holding" or agent.holding_id != holding_id:
            continue
        return agent.key_findings
    return None


def _extract_pscc_portfolio_output(agent_results: Sequence[AgentResult]) -> Optional[Dict[str, Any]]:
    for agent in agent_results:
        if agent.agent_name != "PSCC" or agent.scope != "portfolio":
            continue
        return agent.key_findings
    return None


def _build_summary(
    outcome: RunOutcome,
    reasons: List[str],
    holding_states: Iterable[HoldingState],
) -> Dict[str, Any]:
    counts = {key.value: 0 for key in RunOutcome}
    for state in holding_states:
        counts[state.outcome.value] += 1
    summary = {
        "counts_by_outcome": counts,
    }
    if outcome == RunOutcome.VETOED:
        summary["veto_reasons"] = reasons
    if outcome == RunOutcome.SHORT_CIRCUITED:
        summary["short_circuit_reasons"] = reasons
    return summary


def _sorted_agent_outputs(agent_results: Sequence[AgentResult]) -> List[Dict[str, Any]]:
    return [agent.model_dump() for agent in sorted(agent_results, key=lambda agent: agent.agent_name)]


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


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
