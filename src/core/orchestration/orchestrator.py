from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional

from pydantic import ValidationError

from src.aggregation import HoldingState, build_portfolio_packet
from src.agents.executor import HoldingAgentContext, PortfolioAgentContext, run_holding_agents, run_portfolio_agents
from src.agents.registry import AgentRegistry, get_default_registry
from src.core.governance.engine import GovernanceEngine
from src.core.guards.base import GuardScope, GuardViolation, fail_result, pass_result
from src.core.guards.guards_g0_g10 import GuardContext
from src.core.guards.registry import build_guard_registry
from src.core.logging.runlog import RunLogBuilder
from src.core.models import (
    AgentResult,
    ConfigSnapshot,
    FailedRunPacket,
    GuardResult,
    HoldingInput,
    OrchestrationResult,
    PortfolioCommitteePacket,
    PortfolioConfig,
    PortfolioSnapshot,
    RunConfig,
    RunOutcome,
)
from src.core.penalties import DIOOutput
from src.core.utils.determinism import stable_sort_holdings


DEFAULT_RUN_ID = "local-run"
DEFAULT_TIME = datetime(2025, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class _ParsedInputs:
    portfolio_snapshot: PortfolioSnapshot
    portfolio_config: PortfolioConfig
    run_config: RunConfig
    config_snapshot: ConfigSnapshot
    ordered_holdings: List[HoldingInput]


class Orchestrator:
    def __init__(
        self,
        now_func: Optional[Callable[[], datetime]] = None,
        registry: Optional[AgentRegistry] = None,
    ) -> None:
        self._now_func = now_func or (lambda: DEFAULT_TIME)
        self._registry = registry or get_default_registry()
        self._guards = build_guard_registry()
        self._governance = GovernanceEngine()

    def run(
        self,
        *,
        portfolio_snapshot_data: Dict[str, object],
        portfolio_config_data: Dict[str, object],
        run_config_data: Dict[str, object],
        config_snapshot_data: Dict[str, object],
        manifest_data: Optional[Dict[str, str]] = None,
        config_hashes: Optional[Dict[str, str]] = None,
        run_id: Optional[str] = None,
    ) -> OrchestrationResult:
        run_identifier = run_id or DEFAULT_RUN_ID
        started_at = self._now_func()
        config_hashes = config_hashes or {}
        runlog = RunLogBuilder(
            run_id=run_identifier,
            started_at_utc=started_at,
            config_hashes=config_hashes,
        )

        parsed, schema_errors = self._parse_inputs(
            portfolio_snapshot_data,
            portfolio_config_data,
            run_config_data,
            config_snapshot_data,
        )

        guard_results: List[GuardResult] = []
        guard_violations: List[GuardViolation] = []

        if schema_errors:
            guard_results.append(fail_result("G0", RunOutcome.FAILED, schema_errors))
            runlog.extend_reasons(schema_errors)
            runlog.set_outcome(RunOutcome.FAILED, status="failed")
            failed_packet = self._build_failed_packet(
                run_id=run_identifier,
                portfolio_snapshot=parsed.portfolio_snapshot if parsed else None,
                portfolio_config=parsed.portfolio_config if parsed else None,
                run_config=parsed.run_config if parsed else None,
                reasons=schema_errors,
                config_hashes=config_hashes,
            )
            return OrchestrationResult(
                run_log=runlog.finish(),
                outcome=RunOutcome.FAILED,
                guard_results=guard_results,
                failed_run_packet=failed_packet,
                portfolio_committee_packet=None,
                holding_packets=[],
                ordered_holdings=parsed.ordered_holdings if parsed else [],
            )

        assert parsed is not None

        guard_context = GuardContext(
            portfolio_snapshot=parsed.portfolio_snapshot,
            portfolio_config=parsed.portfolio_config,
            run_config=parsed.run_config,
            config_snapshot=parsed.config_snapshot,
            manifest=manifest_data,
            config_hashes=config_hashes,
            ordered_holdings=parsed.ordered_holdings,
            agent_results=[],
            schema_errors=schema_errors,
        )

        intake_results, intake_violations = self._run_guards(
            guard_context,
            {"G0", "G1", "G2", "G3", "G4"},
        )
        guard_results.extend(intake_results)
        guard_violations.extend(intake_violations)

        portfolio_guard_outcome, guard_reasons = self._portfolio_guard_outcome(intake_results)
        if portfolio_guard_outcome in {RunOutcome.FAILED, RunOutcome.VETOED}:
            runlog.extend_reasons(guard_reasons)
            runlog.set_outcome(portfolio_guard_outcome, status="stopped")
            holding_states = self._build_holding_states(
                parsed.ordered_holdings,
                portfolio_guard_outcome,
                guard_violations,
            )
            packet, holding_packets = self._emit_packets(
                run_id=run_identifier,
                parsed=parsed,
                outcome=portfolio_guard_outcome,
                reasons=guard_reasons,
                holding_states=holding_states,
                agent_results=[],
                guard_results=guard_results,
            )
            failed_packet = packet if isinstance(packet, FailedRunPacket) else None
            committee_packet = packet if isinstance(packet, PortfolioCommitteePacket) else None
            guard_results = self._finalize_guards(
                guard_results,
                outcome=portfolio_guard_outcome,
                failed_packet=failed_packet,
                committee_packet=committee_packet,
            )
            return OrchestrationResult(
                run_log=runlog.finish(),
                outcome=portfolio_guard_outcome,
                guard_results=sorted(guard_results, key=lambda item: item.guard_id),
                failed_run_packet=failed_packet,
                portfolio_committee_packet=committee_packet,
                holding_packets=holding_packets,
                ordered_holdings=parsed.ordered_holdings,
            )

        agent_results = self._run_agents(parsed, guard_violations)
        guard_context = GuardContext(
            portfolio_snapshot=parsed.portfolio_snapshot,
            portfolio_config=parsed.portfolio_config,
            run_config=parsed.run_config,
            config_snapshot=parsed.config_snapshot,
            manifest=manifest_data,
            config_hashes=config_hashes,
            ordered_holdings=parsed.ordered_holdings,
            agent_results=agent_results,
            schema_errors=schema_errors,
        )

        post_agent_results, post_agent_violations = self._run_guards(
            guard_context,
            {"G5", "G6", "G7"},
        )
        guard_results.extend(post_agent_results)
        guard_violations.extend(post_agent_violations)

        portfolio_guard_outcome, guard_reasons = self._portfolio_guard_outcome(post_agent_results)
        if portfolio_guard_outcome == RunOutcome.FAILED:
            runlog.extend_reasons(guard_reasons)
            runlog.set_outcome(RunOutcome.FAILED, status="stopped")
            failed_packet = self._build_failed_packet(
                run_id=run_identifier,
                portfolio_snapshot=parsed.portfolio_snapshot,
                portfolio_config=parsed.portfolio_config,
                run_config=parsed.run_config,
                reasons=guard_reasons,
                config_hashes=config_hashes,
            )
            guard_results = self._finalize_guards(
                guard_results,
                outcome=RunOutcome.FAILED,
                failed_packet=failed_packet,
                committee_packet=None,
            )
            return OrchestrationResult(
                run_log=runlog.finish(),
                outcome=RunOutcome.FAILED,
                guard_results=sorted(guard_results, key=lambda item: item.guard_id),
                failed_run_packet=failed_packet,
                portfolio_committee_packet=None,
                holding_packets=[],
                ordered_holdings=parsed.ordered_holdings,
            )

        governance_decision = self._governance.evaluate(
            ordered_holdings=parsed.ordered_holdings,
            agent_results=agent_results,
            guard_results=guard_results,
            guard_violations=guard_violations,
            run_config=parsed.run_config,
        )

        if governance_decision.portfolio_outcome == RunOutcome.COMPLETED:
            holding_outcomes = [state.outcome for state in governance_decision.holding_states]
            g9_results, g9_violations = self._run_guards(
                guard_context,
                {"G9"},
                holding_outcomes=holding_outcomes,
            )
            guard_results.extend(g9_results)
            guard_violations.extend(g9_violations)
            g9_outcome, g9_reasons = self._portfolio_guard_outcome(g9_results)
            if g9_outcome == RunOutcome.VETOED:
                governance_decision = governance_decision.with_portfolio_override(
                    RunOutcome.VETOED,
                    g9_reasons,
                )

        runlog.extend_reasons(governance_decision.portfolio_reasons)
        runlog.set_outcome(governance_decision.portfolio_outcome, status="completed")

        packet, holding_packets = self._emit_packets(
            run_id=run_identifier,
            parsed=parsed,
            outcome=governance_decision.portfolio_outcome,
            reasons=governance_decision.portfolio_reasons,
            holding_states=governance_decision.holding_states,
            agent_results=agent_results,
            guard_results=guard_results,
        )

        failed_packet = packet if isinstance(packet, FailedRunPacket) else None
        committee_packet = packet if isinstance(packet, PortfolioCommitteePacket) else None

        guard_results = self._finalize_guards(
            guard_results,
            outcome=governance_decision.portfolio_outcome,
            failed_packet=failed_packet,
            committee_packet=committee_packet,
        )

        return OrchestrationResult(
            run_log=runlog.finish(),
            outcome=governance_decision.portfolio_outcome,
            guard_results=sorted(guard_results, key=lambda item: item.guard_id),
            failed_run_packet=failed_packet,
            portfolio_committee_packet=committee_packet,
            holding_packets=holding_packets,
            ordered_holdings=parsed.ordered_holdings,
        )

    def _parse_inputs(
        self,
        portfolio_snapshot_data: Dict[str, object],
        portfolio_config_data: Dict[str, object],
        run_config_data: Dict[str, object],
        config_snapshot_data: Dict[str, object],
    ) -> tuple[Optional[_ParsedInputs], List[str]]:
        errors: List[str] = []
        portfolio_snapshot = None
        portfolio_config = None
        run_config = None
        config_snapshot = None

        try:
            portfolio_snapshot = PortfolioSnapshot.parse_obj(portfolio_snapshot_data)
        except ValidationError as exc:
            errors.extend(self._format_validation_errors(exc, "portfolio_snapshot"))
        try:
            portfolio_config = PortfolioConfig.parse_obj(portfolio_config_data)
        except ValidationError as exc:
            errors.extend(self._format_validation_errors(exc, "portfolio_config"))
        try:
            run_config = RunConfig.parse_obj(run_config_data)
        except ValidationError as exc:
            errors.extend(self._format_validation_errors(exc, "run_config"))
        try:
            config_snapshot = ConfigSnapshot.parse_obj(config_snapshot_data)
        except ValidationError as exc:
            errors.extend(self._format_validation_errors(exc, "config_snapshot"))

        if errors:
            return None, errors

        ordered_holdings = stable_sort_holdings(portfolio_snapshot.holdings)
        portfolio_snapshot = portfolio_snapshot.model_copy(update={"holdings": ordered_holdings})
        return (
            _ParsedInputs(
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                config_snapshot=config_snapshot,
                ordered_holdings=ordered_holdings,
            ),
            [],
        )

    @staticmethod
    def _format_validation_errors(exc: ValidationError, prefix: str) -> List[str]:
        reasons: List[str] = []
        for error in exc.errors():
            loc = "_".join(str(item) for item in error.get("loc", []))
            message = error.get("msg", "invalid")
            suffix = f"{prefix}_{loc}" if loc else prefix
            reasons.append(f"{suffix}:{message}")
        return reasons

    def _run_agents(
        self,
        parsed: _ParsedInputs,
        guard_violations: List[GuardViolation],
    ) -> List[AgentResult]:
        agent_results: List[AgentResult] = []
        terminal_holdings = self._terminal_holdings(parsed, guard_violations)

        portfolio_context = PortfolioAgentContext(
            portfolio_snapshot=parsed.portfolio_snapshot,
            portfolio_config=parsed.portfolio_config,
            run_config=parsed.run_config,
            config_snapshot=parsed.config_snapshot,
            ordered_holdings=parsed.ordered_holdings,
            agent_results=agent_results,
        )
        agent_results.extend(run_portfolio_agents("DIO", portfolio_context, registry=self._registry))
        if self._dio_portfolio_veto(agent_results):
            return self._sorted_agents(agent_results)
        for index, holding in enumerate(parsed.ordered_holdings):
            holding_id = self._holding_id_for(index, holding)
            if holding_id in terminal_holdings:
                continue
            holding_context = HoldingAgentContext(
                holding=holding,
                portfolio_snapshot=parsed.portfolio_snapshot,
                portfolio_config=parsed.portfolio_config,
                run_config=parsed.run_config,
                config_snapshot=parsed.config_snapshot,
                ordered_holdings=parsed.ordered_holdings,
                agent_results=agent_results,
            )
            agent_results.extend(run_holding_agents("DIO", holding_context, registry=self._registry))

        terminal_holdings.update(self._dio_holding_vetoes(agent_results))

        portfolio_context = PortfolioAgentContext(
            portfolio_snapshot=parsed.portfolio_snapshot,
            portfolio_config=parsed.portfolio_config,
            run_config=parsed.run_config,
            config_snapshot=parsed.config_snapshot,
            ordered_holdings=parsed.ordered_holdings,
            agent_results=agent_results,
        )
        agent_results.extend(run_portfolio_agents("GRRA", portfolio_context, registry=self._registry))
        if self._grra_short_circuit(agent_results, parsed.run_config):
            return self._sorted_agents(agent_results)

        for index, holding in enumerate(parsed.ordered_holdings):
            holding_id = self._holding_id_for(index, holding)
            if holding_id in terminal_holdings:
                continue
            holding_context = HoldingAgentContext(
                holding=holding,
                portfolio_snapshot=parsed.portfolio_snapshot,
                portfolio_config=parsed.portfolio_config,
                run_config=parsed.run_config,
                config_snapshot=parsed.config_snapshot,
                ordered_holdings=parsed.ordered_holdings,
                agent_results=agent_results,
            )
            agent_results.extend(
                run_holding_agents("LEFO_PSCC", holding_context, registry=self._registry)
            )

        portfolio_context = PortfolioAgentContext(
            portfolio_snapshot=parsed.portfolio_snapshot,
            portfolio_config=parsed.portfolio_config,
            run_config=parsed.run_config,
            config_snapshot=parsed.config_snapshot,
            ordered_holdings=parsed.ordered_holdings,
            agent_results=agent_results,
        )
        agent_results.extend(run_portfolio_agents("LEFO_PSCC", portfolio_context, registry=self._registry))

        for index, holding in enumerate(parsed.ordered_holdings):
            holding_id = self._holding_id_for(index, holding)
            if holding_id in terminal_holdings:
                continue
            holding_context = HoldingAgentContext(
                holding=holding,
                portfolio_snapshot=parsed.portfolio_snapshot,
                portfolio_config=parsed.portfolio_config,
                run_config=parsed.run_config,
                config_snapshot=parsed.config_snapshot,
                ordered_holdings=parsed.ordered_holdings,
                agent_results=agent_results,
            )
            agent_results.extend(run_holding_agents("RISK_OFFICER", holding_context, registry=self._registry))

        terminal_holdings.update(self._risk_officer_vetoes(agent_results))

        for index, holding in enumerate(parsed.ordered_holdings):
            holding_id = self._holding_id_for(index, holding)
            if holding_id in terminal_holdings:
                continue
            holding_context = HoldingAgentContext(
                holding=holding,
                portfolio_snapshot=parsed.portfolio_snapshot,
                portfolio_config=parsed.portfolio_config,
                run_config=parsed.run_config,
                config_snapshot=parsed.config_snapshot,
                ordered_holdings=parsed.ordered_holdings,
                agent_results=agent_results,
            )
            agent_results.extend(run_holding_agents("ANALYTICAL", holding_context, registry=self._registry))

        return self._sorted_agents(agent_results)

    @staticmethod
    def _dio_portfolio_veto(agent_results: Iterable[AgentResult]) -> bool:
        for agent in agent_results:
            if agent.agent_name != "DIO" or agent.scope != "portfolio":
                continue
            if Orchestrator._dio_output_veto(agent.key_findings):
                return True
        return False

    @staticmethod
    def _dio_holding_vetoes(agent_results: Iterable[AgentResult]) -> set[str]:
        vetoed: set[str] = set()
        for agent in agent_results:
            if agent.agent_name != "DIO" or agent.scope != "holding":
                continue
            if Orchestrator._dio_output_veto(agent.key_findings):
                if agent.holding_id:
                    vetoed.add(agent.holding_id)
        return vetoed

    @staticmethod
    def _risk_officer_vetoes(agent_results: Iterable[AgentResult]) -> set[str]:
        vetoed: set[str] = set()
        for agent in agent_results:
            if agent.agent_name != "RiskOfficer" or agent.scope != "holding":
                continue
            if agent.veto_flags and agent.holding_id:
                vetoed.add(agent.holding_id)
        return vetoed

    @staticmethod
    def _grra_short_circuit(agent_results: Iterable[AgentResult], run_config: RunConfig) -> bool:
        if run_config.do_not_trade_flag:
            return True
        for agent in agent_results:
            if agent.agent_name != "GRRA" or agent.scope != "portfolio":
                continue
            if agent.key_findings.get("do_not_trade_flag") is True:
                return True
        return False

    @staticmethod
    def _dio_output_veto(payload: Dict[str, object]) -> bool:
        try:
            dio_output = DIOOutput.parse_obj(payload)
        except ValidationError:
            return False
        if dio_output.integrity_veto_triggered:
            return True
        if dio_output.unsourced_numbers_detected:
            return True
        if dio_output.missing_hard_stop_fields:
            return True
        if any(flag.hard_stop_triggered for flag in dio_output.staleness_flags):
            return True
        return False

    def _terminal_holdings(
        self,
        parsed: _ParsedInputs,
        guard_violations: List[GuardViolation],
    ) -> set[str]:
        terminal: set[str] = set()
        for violation in guard_violations:
            if violation.scope != GuardScope.HOLDING:
                continue
            if violation.outcome not in {RunOutcome.FAILED, RunOutcome.VETOED, RunOutcome.SHORT_CIRCUITED}:
                continue
            holding_id = violation.holding_id
            if not holding_id and violation.holding_index is not None:
                if 0 <= violation.holding_index < len(parsed.ordered_holdings):
                    holding_id = self._holding_id_for(
                        violation.holding_index,
                        parsed.ordered_holdings[violation.holding_index],
                    )
            if holding_id:
                terminal.add(holding_id)
        return terminal

    @staticmethod
    def _sorted_agents(results: Iterable[AgentResult]) -> List[AgentResult]:
        return sorted(
            list(results),
            key=lambda item: (
                item.agent_name,
                item.scope,
                item.holding_id or "",
            ),
        )

    def _run_guards(
        self,
        context: GuardContext,
        guard_ids: set[str],
        *,
        holding_outcomes: Optional[List[RunOutcome]] = None,
    ) -> tuple[List[GuardResult], List[GuardViolation]]:
        results: List[GuardResult] = []
        violations: List[GuardViolation] = []
        for guard in self._guards:
            if guard.guard_id not in guard_ids:
                continue
            if guard.guard_id == "G9":
                if holding_outcomes is None:
                    results.append(GuardResult(guard_id="G9", status="skipped", outcome=None, reasons=[]))
                    continue
                evaluation = guard.evaluate(context=context, holding_outcomes=holding_outcomes)
            else:
                evaluation = guard.evaluate(context=context)
            results.append(evaluation.result)
            violations.extend(evaluation.violations)
        return results, violations

    @staticmethod
    def _portfolio_guard_outcome(guard_results: Iterable[GuardResult]) -> tuple[Optional[RunOutcome], List[str]]:
        for result in guard_results:
            if result.outcome is not None:
                return result.outcome, result.reasons
        return None, []

    def _build_holding_states(
        self,
        ordered_holdings: List[HoldingInput],
        fallback_outcome: RunOutcome,
        guard_violations: List[GuardViolation],
    ) -> List[HoldingState]:
        holding_states: List[HoldingState] = []
        reasons_by_id: Dict[str, List[str]] = {}
        for violation in guard_violations:
            if violation.scope != GuardScope.HOLDING:
                continue
            holding_id = violation.holding_id or ""
            reasons_by_id.setdefault(holding_id, []).append(violation.reason)

        for index, holding in enumerate(ordered_holdings):
            holding_id = self._holding_id_for(index, holding)
            reasons = reasons_by_id.get(holding_id, [])
            outcome = fallback_outcome
            if reasons:
                outcome = RunOutcome.FAILED
            holding_states.append(HoldingState(holding=holding, outcome=outcome, reasons=reasons))
        return holding_states

    def _emit_packets(
        self,
        *,
        run_id: str,
        parsed: _ParsedInputs,
        outcome: RunOutcome,
        reasons: List[str],
        holding_states: List[HoldingState],
        agent_results: List[AgentResult],
        guard_results: List[GuardResult],
    ) -> tuple[PortfolioCommitteePacket | FailedRunPacket, List]:
        packet = build_portfolio_packet(
            run_id=run_id,
            portfolio_snapshot=parsed.portfolio_snapshot,
            portfolio_config=parsed.portfolio_config,
            run_config=parsed.run_config,
            config_snapshot=parsed.config_snapshot,
            outcome=outcome,
            reasons=reasons,
            holding_states=holding_states,
            agent_results=agent_results,
            guard_results=guard_results,
        )
        holding_packets = []
        if isinstance(packet, PortfolioCommitteePacket):
            holding_packets = packet.holdings
        return packet, holding_packets

    def _build_failed_packet(
        self,
        *,
        run_id: str,
        portfolio_snapshot: Optional[PortfolioSnapshot],
        portfolio_config: Optional[PortfolioConfig],
        run_config: Optional[RunConfig],
        reasons: List[str],
        config_hashes: Dict[str, str],
    ) -> FailedRunPacket:
        return FailedRunPacket(
            run_id=run_id,
            portfolio_run_outcome=RunOutcome.FAILED,
            failure_reason=reasons[0] if reasons else "unknown_failure",
            reasons=reasons,
            portfolio_id=portfolio_snapshot.portfolio_id if portfolio_snapshot else None,
            as_of_date=portfolio_snapshot.as_of_date if portfolio_snapshot else None,
            base_currency=portfolio_config.base_currency if portfolio_config else None,
            run_mode=run_config.run_mode if run_config else None,
            config_hashes=config_hashes,
        )

    def _finalize_guards(
        self,
        guard_results: List[GuardResult],
        *,
        outcome: RunOutcome,
        failed_packet: Optional[FailedRunPacket],
        committee_packet: Optional[PortfolioCommitteePacket],
    ) -> List[GuardResult]:
        guard_results = list(guard_results)
        guard_results.append(self._evaluate_error_classification(outcome, guard_results))
        guard_results.append(
            self._evaluate_emission_eligibility(outcome, failed_packet, committee_packet)
        )
        return guard_results

    @staticmethod
    def _evaluate_error_classification(
        outcome: RunOutcome,
        guard_results: List[GuardResult],
    ) -> GuardResult:
        if outcome == RunOutcome.COMPLETED and any(result.outcome for result in guard_results):
            return fail_result("G8", RunOutcome.FAILED, ["outcome_conflict"])
        return pass_result("G8")

    @staticmethod
    def _evaluate_emission_eligibility(
        outcome: RunOutcome,
        failed_packet: Optional[FailedRunPacket],
        committee_packet: Optional[PortfolioCommitteePacket],
    ) -> GuardResult:
        reasons: List[str] = []
        if outcome == RunOutcome.FAILED:
            if failed_packet is None:
                reasons.append("failed_packet_missing")
            if committee_packet is not None:
                reasons.append("committee_packet_not_allowed")
        elif outcome == RunOutcome.COMPLETED:
            if committee_packet is None:
                reasons.append("committee_packet_missing")
            else:
                if committee_packet.snapshot_hash is None:
                    reasons.append("snapshot_hash_missing")
                if committee_packet.config_hash is None:
                    reasons.append("config_hash_missing")
                if committee_packet.run_config_hash is None:
                    reasons.append("run_config_hash_missing")
                if committee_packet.committee_packet_hash is None:
                    reasons.append("committee_packet_hash_missing")
                if committee_packet.decision_hash is None:
                    reasons.append("decision_hash_missing")
                if committee_packet.run_hash is None:
                    reasons.append("run_hash_missing")
        else:
            if committee_packet is None:
                reasons.append("committee_packet_missing")
            else:
                if committee_packet.committee_packet_hash is not None:
                    reasons.append("hashes_not_allowed")
                if committee_packet.decision_hash is not None:
                    reasons.append("hashes_not_allowed")
                if committee_packet.run_hash is not None:
                    reasons.append("hashes_not_allowed")
        if reasons:
            return fail_result("G10", RunOutcome.FAILED, reasons)
        return pass_result("G10")

    @staticmethod
    def _holding_id_for(index: int, holding: HoldingInput) -> str:
        if holding.identity and holding.identity.holding_id:
            return holding.identity.holding_id
        return f"holding_index_{index}"
