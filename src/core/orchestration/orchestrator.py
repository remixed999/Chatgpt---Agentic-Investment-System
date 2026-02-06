from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import ValidationError

from src.agents.executor import (
    HoldingAgentContext,
    PortfolioAgentContext,
    run_holding_agents,
    run_portfolio_agents,
)
from src.aggregation.aggregator import HoldingState as AggregationHoldingState, build_portfolio_packet
from src.core.guards.base import GuardEvaluation, GuardScope
from src.core.guards.guards_g0_g10 import GuardContext
from src.core.guards.registry import build_guard_registry
from src.core.models import (
    AgentResult,
    ConfigSnapshot,
    FailedRunPacket,
    GuardResult,
    HoldingInput,
    HoldingPacket,
    OrchestrationResult,
    PortfolioConfig,
    PortfolioSnapshot,
    RunConfig,
    RunLog,
    RunOutcome,
)
from src.core.utils.determinism import stable_sort_holdings


class Orchestrator:
    def __init__(self, now_func: Optional[Callable[[], datetime]] = None) -> None:
        self._now_func = now_func or (lambda: datetime.now(timezone.utc))
        self._guards = build_guard_registry()
        self._guards_by_id = {guard.guard_id: guard for guard in self._guards}

    def run(
        self,
        *,
        portfolio_snapshot_data: Dict[str, Any],
        portfolio_config_data: Dict[str, Any],
        run_config_data: Dict[str, Any],
        config_snapshot_data: Dict[str, Any],
        manifest_data: Optional[Dict[str, str]],
        config_hashes: Dict[str, str],
        agent_results_data: Optional[List[Dict[str, Any]]] = None,
        run_id: Optional[str] = None,
    ) -> OrchestrationResult:
        run_identifier = run_id or str(uuid4())
        started_at = self._now_func()
        guard_results = []
        agent_results = []

        try:
            portfolio_snapshot = PortfolioSnapshot.parse_obj(portfolio_snapshot_data)
            portfolio_config = PortfolioConfig.parse_obj(portfolio_config_data)
            run_config = RunConfig.parse_obj(run_config_data)
            config_snapshot = ConfigSnapshot.parse_obj(config_snapshot_data)
        except ValidationError as exc:
            reasons = [self._format_error(error) for error in exc.errors()]
            return self._build_failure_result(
                run_id=run_identifier,
                started_at=started_at,
                outcome=RunOutcome.FAILED,
                reasons=reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=None,
                portfolio_config=None,
                run_config=None,
            )

        ordered_holdings = stable_sort_holdings(portfolio_snapshot.holdings)
        holding_states = [
            AggregationHoldingState(holding=holding, outcome=RunOutcome.COMPLETED, reasons=[])
            for holding in ordered_holdings
        ]
        agent_results = self._parse_agent_results(agent_results_data)

        context = GuardContext(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            manifest=manifest_data,
            config_hashes=config_hashes,
            ordered_holdings=ordered_holdings,
            agent_results=agent_results,
        )

        for guard_id in ("G0", "G1", "G2", "G3", "G4", "G7"):
            evaluation = self._evaluate_guard(
                guard_id=guard_id,
                context=context,
                guard_results=guard_results,
                holding_states=holding_states,
                holding_outcomes=[state.outcome for state in holding_states],
            )
            if evaluation and evaluation.result.outcome:
                if evaluation.result.outcome == RunOutcome.SHORT_CIRCUITED:
                    self._apply_short_circuit(holding_states)
                return self._finalize_result(
                    run_id=run_identifier,
                    started_at=started_at,
                    outcome=evaluation.result.outcome,
                    reasons=evaluation.result.reasons,
                    config_hashes=config_hashes,
                    portfolio_snapshot=portfolio_snapshot,
                    portfolio_config=portfolio_config,
                    run_config=run_config,
                    config_snapshot=config_snapshot,
                    guard_results=guard_results,
                    ordered_holdings=ordered_holdings,
                    holding_states=holding_states,
                    agent_results=agent_results,
                )

        agent_results.extend(self._run_phase_dio(ordered_holdings, portfolio_snapshot, portfolio_config, run_config, config_snapshot, agent_results, holding_states))
        context = self._build_guard_context(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            manifest=manifest_data,
            config_hashes=config_hashes,
            ordered_holdings=ordered_holdings,
            agent_results=agent_results,
        )
        evaluation = self._evaluate_guard(
            guard_id="G5",
            context=context,
            guard_results=guard_results,
            holding_states=holding_states,
            holding_outcomes=[state.outcome for state in holding_states],
        )
        if evaluation and evaluation.result.outcome:
            if evaluation.result.outcome == RunOutcome.SHORT_CIRCUITED:
                self._apply_short_circuit(holding_states)
            return self._finalize_result(
                run_id=run_identifier,
                started_at=started_at,
                outcome=evaluation.result.outcome,
                reasons=evaluation.result.reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                guard_results=guard_results,
                ordered_holdings=ordered_holdings,
                holding_states=holding_states,
                agent_results=agent_results,
            )

        portfolio_veto_reasons = self._apply_dio_vetoes(agent_results, holding_states)
        if portfolio_veto_reasons:
            return self._finalize_result(
                run_id=run_identifier,
                started_at=started_at,
                outcome=RunOutcome.VETOED,
                reasons=portfolio_veto_reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                guard_results=guard_results,
                ordered_holdings=ordered_holdings,
                holding_states=holding_states,
                agent_results=agent_results,
            )

        agent_results.extend(self._run_phase_grra(ordered_holdings, portfolio_snapshot, portfolio_config, run_config, config_snapshot, agent_results))
        context = self._build_guard_context(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            manifest=manifest_data,
            config_hashes=config_hashes,
            ordered_holdings=ordered_holdings,
            agent_results=agent_results,
        )
        evaluation = self._evaluate_guard(
            guard_id="G5",
            context=context,
            guard_results=guard_results,
            holding_states=holding_states,
            holding_outcomes=[state.outcome for state in holding_states],
        )
        if evaluation and evaluation.result.outcome:
            if evaluation.result.outcome == RunOutcome.SHORT_CIRCUITED:
                self._apply_short_circuit(holding_states)
            return self._finalize_result(
                run_id=run_identifier,
                started_at=started_at,
                outcome=evaluation.result.outcome,
                reasons=evaluation.result.reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                guard_results=guard_results,
                ordered_holdings=ordered_holdings,
                holding_states=holding_states,
                agent_results=agent_results,
            )

        evaluation = self._evaluate_guard(
            guard_id="G6",
            context=context,
            guard_results=guard_results,
            holding_states=holding_states,
            holding_outcomes=[state.outcome for state in holding_states],
        )
        if evaluation and evaluation.result.outcome:
            if evaluation.result.outcome == RunOutcome.SHORT_CIRCUITED:
                self._apply_short_circuit(holding_states)
            return self._finalize_result(
                run_id=run_identifier,
                started_at=started_at,
                outcome=evaluation.result.outcome,
                reasons=evaluation.result.reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                guard_results=guard_results,
                ordered_holdings=ordered_holdings,
                holding_states=holding_states,
                agent_results=agent_results,
            )

        agent_results.extend(
            self._run_phase_lefo_pscc(
                ordered_holdings,
                portfolio_snapshot,
                portfolio_config,
                run_config,
                config_snapshot,
                agent_results,
                holding_states,
            )
        )
        context = self._build_guard_context(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            manifest=manifest_data,
            config_hashes=config_hashes,
            ordered_holdings=ordered_holdings,
            agent_results=agent_results,
        )
        evaluation = self._evaluate_guard(
            guard_id="G5",
            context=context,
            guard_results=guard_results,
            holding_states=holding_states,
            holding_outcomes=[state.outcome for state in holding_states],
        )
        if evaluation and evaluation.result.outcome:
            if evaluation.result.outcome == RunOutcome.SHORT_CIRCUITED:
                self._apply_short_circuit(holding_states)
            return self._finalize_result(
                run_id=run_identifier,
                started_at=started_at,
                outcome=evaluation.result.outcome,
                reasons=evaluation.result.reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                guard_results=guard_results,
                ordered_holdings=ordered_holdings,
                holding_states=holding_states,
                agent_results=agent_results,
            )

        agent_results.extend(
            self._run_phase_risk_officer(
                ordered_holdings,
                portfolio_snapshot,
                portfolio_config,
                run_config,
                config_snapshot,
                agent_results,
                holding_states,
            )
        )
        context = self._build_guard_context(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            manifest=manifest_data,
            config_hashes=config_hashes,
            ordered_holdings=ordered_holdings,
            agent_results=agent_results,
        )
        evaluation = self._evaluate_guard(
            guard_id="G5",
            context=context,
            guard_results=guard_results,
            holding_states=holding_states,
            holding_outcomes=[state.outcome for state in holding_states],
        )
        if evaluation and evaluation.result.outcome:
            if evaluation.result.outcome == RunOutcome.SHORT_CIRCUITED:
                self._apply_short_circuit(holding_states)
            return self._finalize_result(
                run_id=run_identifier,
                started_at=started_at,
                outcome=evaluation.result.outcome,
                reasons=evaluation.result.reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                guard_results=guard_results,
                ordered_holdings=ordered_holdings,
                holding_states=holding_states,
                agent_results=agent_results,
            )

        agent_results.extend(
            self._run_phase_analytical(
                ordered_holdings,
                portfolio_snapshot,
                portfolio_config,
                run_config,
                config_snapshot,
                agent_results,
                holding_states,
            )
        )
        context = self._build_guard_context(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            manifest=manifest_data,
            config_hashes=config_hashes,
            ordered_holdings=ordered_holdings,
            agent_results=agent_results,
        )
        evaluation = self._evaluate_guard(
            guard_id="G5",
            context=context,
            guard_results=guard_results,
            holding_states=holding_states,
            holding_outcomes=[state.outcome for state in holding_states],
        )
        if evaluation and evaluation.result.outcome:
            if evaluation.result.outcome == RunOutcome.SHORT_CIRCUITED:
                self._apply_short_circuit(holding_states)
            return self._finalize_result(
                run_id=run_identifier,
                started_at=started_at,
                outcome=evaluation.result.outcome,
                reasons=evaluation.result.reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                guard_results=guard_results,
                ordered_holdings=ordered_holdings,
                holding_states=holding_states,
                agent_results=agent_results,
            )

        evaluation = self._evaluate_guard(
            guard_id="G9",
            context=context,
            guard_results=guard_results,
            holding_states=holding_states,
            holding_outcomes=[state.outcome for state in holding_states],
        )
        if evaluation and evaluation.result.outcome:
            if evaluation.result.outcome == RunOutcome.SHORT_CIRCUITED:
                self._apply_short_circuit(holding_states)
            return self._finalize_result(
                run_id=run_identifier,
                started_at=started_at,
                outcome=evaluation.result.outcome,
                reasons=evaluation.result.reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                guard_results=guard_results,
                ordered_holdings=ordered_holdings,
                holding_states=holding_states,
                agent_results=agent_results,
            )

        for guard_id in ("G8", "G10"):
            evaluation = self._evaluate_guard(
                guard_id=guard_id,
                context=context,
                guard_results=guard_results,
                holding_states=holding_states,
                holding_outcomes=[state.outcome for state in holding_states],
            )
            if evaluation and evaluation.result.outcome:
                if evaluation.result.outcome == RunOutcome.SHORT_CIRCUITED:
                    self._apply_short_circuit(holding_states)
                return self._finalize_result(
                    run_id=run_identifier,
                    started_at=started_at,
                    outcome=evaluation.result.outcome,
                    reasons=evaluation.result.reasons,
                    config_hashes=config_hashes,
                    portfolio_snapshot=portfolio_snapshot,
                    portfolio_config=portfolio_config,
                    run_config=run_config,
                    config_snapshot=config_snapshot,
                    guard_results=guard_results,
                    ordered_holdings=ordered_holdings,
                    holding_states=holding_states,
                    agent_results=agent_results,
                )

        return self._finalize_result(
            run_id=run_identifier,
            started_at=started_at,
            outcome=RunOutcome.COMPLETED,
            reasons=[],
            config_hashes=config_hashes,
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            guard_results=guard_results,
            ordered_holdings=ordered_holdings,
            holding_states=holding_states,
            agent_results=agent_results,
        )

    @staticmethod
    def _build_guard_context(
        *,
        portfolio_snapshot: PortfolioSnapshot,
        portfolio_config: PortfolioConfig,
        run_config: RunConfig,
        config_snapshot: ConfigSnapshot,
        manifest: Optional[Dict[str, str]],
        config_hashes: Dict[str, str],
        ordered_holdings: List[HoldingInput],
        agent_results: List[AgentResult],
    ) -> GuardContext:
        return GuardContext(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            manifest=manifest,
            config_hashes=config_hashes,
            ordered_holdings=ordered_holdings,
            agent_results=agent_results,
        )

    def _evaluate_guard(
        self,
        *,
        guard_id: str,
        context: GuardContext,
        guard_results: List[Any],
        holding_states: List[AggregationHoldingState],
        holding_outcomes: List[RunOutcome],
    ) -> Optional[GuardEvaluation]:
        guard = self._guards_by_id[guard_id]
        if guard_id == "G9":
            evaluation = guard.evaluate(context=context, holding_outcomes=holding_outcomes)
        else:
            evaluation = guard.evaluate(context=context)
        guard_results.append(evaluation.result)
        self._apply_violations(holding_states, evaluation)
        return evaluation

    def _parse_agent_results(self, agent_results_data: Optional[List[Dict[str, Any]]]) -> List[AgentResult]:
        if not agent_results_data:
            return []
        results: List[AgentResult] = []
        for item in agent_results_data:
            try:
                results.append(AgentResult.parse_obj(item))
            except ValidationError:
                results.append(
                    AgentResult(
                        agent_name=item.get("agent_name", "UNKNOWN"),
                        scope=item.get("scope", "portfolio"),
                        status="failed",
                        confidence=0.0,
                        key_findings={"conformance_error": True, "error": "invalid_agent_result"},
                        metrics=[],
                        suggested_penalties=[],
                        veto_flags=[],
                        holding_id=item.get("holding_id"),
                    )
                )
        return results

    def _run_phase_dio(
        self,
        ordered_holdings: List[HoldingInput],
        portfolio_snapshot: PortfolioSnapshot,
        portfolio_config: PortfolioConfig,
        run_config: RunConfig,
        config_snapshot: ConfigSnapshot,
        agent_results: List[AgentResult],
        holding_states: List[AggregationHoldingState],
    ) -> List[AgentResult]:
        portfolio_context = PortfolioAgentContext(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            ordered_holdings=ordered_holdings,
            agent_results=agent_results,
        )
        results = run_portfolio_agents("DIO", portfolio_context)
        for state in holding_states:
            if state.outcome != RunOutcome.COMPLETED:
                continue
            holding_context = HoldingAgentContext(
                holding=state.holding,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                ordered_holdings=ordered_holdings,
                agent_results=agent_results + results,
            )
            results.extend(run_holding_agents("DIO", holding_context))
        return results

    def _run_phase_grra(
        self,
        ordered_holdings: List[HoldingInput],
        portfolio_snapshot: PortfolioSnapshot,
        portfolio_config: PortfolioConfig,
        run_config: RunConfig,
        config_snapshot: ConfigSnapshot,
        agent_results: List[AgentResult],
    ) -> List[AgentResult]:
        portfolio_context = PortfolioAgentContext(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            ordered_holdings=ordered_holdings,
            agent_results=agent_results,
        )
        return run_portfolio_agents("GRRA", portfolio_context)

    def _run_phase_lefo_pscc(
        self,
        ordered_holdings: List[HoldingInput],
        portfolio_snapshot: PortfolioSnapshot,
        portfolio_config: PortfolioConfig,
        run_config: RunConfig,
        config_snapshot: ConfigSnapshot,
        agent_results: List[AgentResult],
        holding_states: List[AggregationHoldingState],
    ) -> List[AgentResult]:
        results: List[AgentResult] = []
        for state in holding_states:
            if state.outcome != RunOutcome.COMPLETED:
                continue
            holding_context = HoldingAgentContext(
                holding=state.holding,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                ordered_holdings=ordered_holdings,
                agent_results=agent_results + results,
            )
            results.extend(run_holding_agents("LEFO_PSCC", holding_context))

        portfolio_context = PortfolioAgentContext(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            ordered_holdings=ordered_holdings,
            agent_results=agent_results + results,
        )
        results.extend(run_portfolio_agents("LEFO_PSCC", portfolio_context))
        return results

    def _run_phase_risk_officer(
        self,
        ordered_holdings: List[HoldingInput],
        portfolio_snapshot: PortfolioSnapshot,
        portfolio_config: PortfolioConfig,
        run_config: RunConfig,
        config_snapshot: ConfigSnapshot,
        agent_results: List[AgentResult],
        holding_states: List[AggregationHoldingState],
    ) -> List[AgentResult]:
        results: List[AgentResult] = []
        for state in holding_states:
            if state.outcome != RunOutcome.COMPLETED:
                continue
            holding_context = HoldingAgentContext(
                holding=state.holding,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                ordered_holdings=ordered_holdings,
                agent_results=agent_results + results,
            )
            results.extend(run_holding_agents("RISK_OFFICER", holding_context))
        self._apply_risk_officer_vetoes(results, holding_states)
        return results

    def _run_phase_analytical(
        self,
        ordered_holdings: List[HoldingInput],
        portfolio_snapshot: PortfolioSnapshot,
        portfolio_config: PortfolioConfig,
        run_config: RunConfig,
        config_snapshot: ConfigSnapshot,
        agent_results: List[AgentResult],
        holding_states: List[AggregationHoldingState],
    ) -> List[AgentResult]:
        results: List[AgentResult] = []
        for state in holding_states:
            if state.outcome != RunOutcome.COMPLETED:
                continue
            holding_context = HoldingAgentContext(
                holding=state.holding,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                ordered_holdings=ordered_holdings,
                agent_results=agent_results + results,
            )
            results.extend(run_holding_agents("ANALYTICAL", holding_context))
        return results

    @staticmethod
    def _apply_dio_vetoes(
        agent_results: List[AgentResult],
        holding_states: List[AggregationHoldingState],
    ) -> List[str]:
        portfolio_reasons: List[str] = []
        for agent in agent_results:
            if agent.agent_name != "DIO":
                continue
            if agent.scope == "portfolio":
                if Orchestrator._dio_hard_stop_triggered(agent.key_findings):
                    portfolio_reasons.append("dio_portfolio_veto")
                continue
            if agent.scope != "holding":
                continue
            for state in holding_states:
                if state.holding.identity and state.holding.identity.holding_id == agent.holding_id:
                    if state.outcome != RunOutcome.COMPLETED:
                        break
                    if Orchestrator._dio_hard_stop_triggered(agent.key_findings):
                        state.outcome = RunOutcome.VETOED
                        state.reasons.append("dio_hard_stop")
                    break
        return portfolio_reasons

    @staticmethod
    def _apply_risk_officer_vetoes(
        agent_results: List[AgentResult],
        holding_states: List[AggregationHoldingState],
    ) -> None:
        for agent in agent_results:
            if agent.agent_name != "RiskOfficer" or agent.scope != "holding":
                continue
            if not agent.veto_flags:
                continue
            for state in holding_states:
                if state.outcome != RunOutcome.COMPLETED:
                    continue
                if state.holding.identity and state.holding.identity.holding_id == agent.holding_id:
                    state.outcome = RunOutcome.VETOED
                    state.reasons.append("risk_officer_veto")
                    break

    @staticmethod
    def _dio_hard_stop_triggered(key_findings: Dict[str, Any]) -> bool:
        if key_findings.get("integrity_veto_triggered"):
            return True
        if key_findings.get("unsourced_numbers_detected"):
            return True
        if key_findings.get("missing_hard_stop_fields"):
            return True
        for flag in key_findings.get("staleness_flags", []):
            if flag.get("hard_stop_triggered"):
                return True
        for contradiction in key_findings.get("contradictions", []):
            if contradiction.get("unresolved"):
                return True
        return False

    def _apply_violations(self, holding_states: List[AggregationHoldingState], evaluation: GuardEvaluation) -> None:
        for violation in evaluation.violations:
            if violation.scope != GuardScope.HOLDING:
                continue
            if violation.holding_index is not None and 0 <= violation.holding_index < len(holding_states):
                state = holding_states[violation.holding_index]
            else:
                matching = None
                for state in holding_states:
                    if state.holding.identity and state.holding.identity.holding_id == violation.holding_id:
                        matching = state
                        break
                if matching is None:
                    continue
                state = matching
            if state.outcome != RunOutcome.COMPLETED:
                continue
            state.outcome = violation.outcome
            state.reasons.append(violation.reason)

    @staticmethod
    def _apply_short_circuit(holding_states: List[AggregationHoldingState]) -> None:
        for state in holding_states:
            if state.outcome == RunOutcome.COMPLETED:
                state.outcome = RunOutcome.SHORT_CIRCUITED
                state.reasons.append("short_circuited")

    def _finalize_result(
        self,
        *,
        run_id: str,
        started_at: datetime,
        outcome: RunOutcome,
        reasons: List[str],
        config_hashes: Dict[str, str],
        portfolio_snapshot: PortfolioSnapshot,
        portfolio_config: PortfolioConfig,
        run_config: RunConfig,
        config_snapshot: ConfigSnapshot,
        guard_results: List[Any],
        ordered_holdings: List[HoldingInput],
        holding_states: List[AggregationHoldingState],
        agent_results: List[AgentResult],
    ) -> OrchestrationResult:
        ended_at = self._now_func()
        run_log = RunLog(
            run_id=run_id,
            started_at_utc=started_at,
            ended_at_utc=ended_at,
            status="terminal",
            outcome=outcome,
            reasons=reasons,
            config_hashes=config_hashes,
        )

        packet_or_failure = build_portfolio_packet(
            run_id=run_id,
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            config_snapshot=config_snapshot,
            outcome=outcome,
            reasons=reasons,
            holding_states=holding_states,
            agent_results=agent_results,
            guard_results=guard_results,
        )

        if isinstance(packet_or_failure, FailedRunPacket):
            return OrchestrationResult(
                run_log=run_log,
                outcome=outcome,
                guard_results=guard_results,
                failed_run_packet=packet_or_failure,
                holding_packets=[],
                ordered_holdings=ordered_holdings,
            )

        holding_packets = list(packet_or_failure.holdings)
        return OrchestrationResult(
            run_log=run_log,
            outcome=outcome,
            guard_results=guard_results,
            portfolio_committee_packet=packet_or_failure,
            holding_packets=holding_packets,
            ordered_holdings=ordered_holdings,
        )

    def _build_failure_result(
        self,
        *,
        run_id: str,
        started_at: datetime,
        outcome: RunOutcome,
        reasons: List[str],
        config_hashes: Dict[str, str],
        portfolio_snapshot: Optional[PortfolioSnapshot],
        portfolio_config: Optional[PortfolioConfig],
        run_config: Optional[RunConfig],
        guard_results: Optional[List[Any]] = None,
        ordered_holdings: Optional[List[Any]] = None,
    ) -> OrchestrationResult:
        ended_at = self._now_func()
        run_log = RunLog(
            run_id=run_id,
            started_at_utc=started_at,
            ended_at_utc=ended_at,
            status="terminal",
            outcome=outcome,
            reasons=reasons,
            config_hashes=config_hashes,
        )
        failed_run_packet = FailedRunPacket(
            run_id=run_id,
            portfolio_run_outcome=outcome,
            failure_reason=reasons[0] if reasons else "unknown_failure",
            reasons=reasons,
            portfolio_id=portfolio_snapshot.portfolio_id if portfolio_snapshot else None,
            as_of_date=portfolio_snapshot.as_of_date if portfolio_snapshot else None,
            base_currency=portfolio_config.base_currency if portfolio_config else None,
            run_mode=run_config.run_mode if run_config else None,
            config_hashes=config_hashes,
        )
        return OrchestrationResult(
            run_log=run_log,
            outcome=outcome,
            guard_results=guard_results or [],
            failed_run_packet=failed_run_packet,
            holding_packets=[],
            ordered_holdings=ordered_holdings or [],
        )

    @staticmethod
    def _format_error(error: Dict[str, Any]) -> str:
        location = ".".join(str(item) for item in error.get("loc", []))
        message = error.get("msg", "schema_validation_error")
        if location:
            return f"{location}:{message}"
        return message
