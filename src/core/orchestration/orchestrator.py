from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import ValidationError

from src.core.canonicalization.hashing import RunHashes, compute_run_hashes
from src.core.guards.base import GuardEvaluation, GuardScope
from src.core.guards.guards_g0_g10 import GuardContext
from src.core.guards.registry import build_guard_registry
from src.core.models import (
    AgentResult,
    CommitteePacket,
    CompletedRunPacket,
    ConfigSnapshot,
    DecisionPacket,
    FailedRunPacket,
    HashBundle,
    HoldingInput,
    HoldingPacket,
    OrchestrationResult,
    PortfolioConfig,
    PortfolioSnapshot,
    RunConfig,
    RunLog,
    RunOutcome,
    ShortCircuitRunPacket,
)
from src.core.utils.determinism import stable_sort_holdings


@dataclass
class HoldingState:
    holding: HoldingInput
    outcome: RunOutcome = RunOutcome.COMPLETED
    reasons: List[str] = field(default_factory=list)

    def to_packet(self) -> HoldingPacket:
        return HoldingPacket(
            holding_id=self.holding.identity.holding_id if self.holding.identity else None,
            outcome=self.outcome,
            reasons=self.reasons,
            identity=self.holding.identity,
        )


class Orchestrator:
    def __init__(self, now_func: Optional[Callable[[], datetime]] = None) -> None:
        self._now_func = now_func or (lambda: datetime.now(timezone.utc))
        self._guards = build_guard_registry()

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
            if agent_results_data:
                agent_results = [AgentResult.parse_obj(item) for item in agent_results_data]
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
        holding_states = [HoldingState(holding=holding) for holding in ordered_holdings]

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

        for guard in self._guards:
            if guard.guard_id == "G9":
                evaluation = guard.evaluate(
                    context=context,
                    holding_outcomes=[state.outcome for state in holding_states],
                )
            else:
                evaluation = guard.evaluate(context=context)
            guard_results.append(evaluation.result)
            self._apply_violations(holding_states, evaluation)
            if evaluation.result.outcome:
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
                    guard_results=guard_results,
                    ordered_holdings=ordered_holdings,
                    holding_states=holding_states,
                )

            if guard.guard_id == "G6":
                context = GuardContext(
                    portfolio_snapshot=portfolio_snapshot,
                    portfolio_config=portfolio_config,
                    run_config=run_config,
                    config_snapshot=config_snapshot,
                    manifest=manifest_data,
                    config_hashes=config_hashes,
                    ordered_holdings=ordered_holdings,
                    agent_results=agent_results,
                    portfolio_outcome=None,
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
            guard_results=guard_results,
            ordered_holdings=ordered_holdings,
            holding_states=holding_states,
        )

    def _apply_violations(self, holding_states: List[HoldingState], evaluation: GuardEvaluation) -> None:
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
    def _apply_short_circuit(holding_states: List[HoldingState]) -> None:
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
        guard_results: List[Any],
        ordered_holdings: List[HoldingInput],
        holding_states: List[HoldingState],
    ) -> OrchestrationResult:
        if outcome == RunOutcome.COMPLETED:
            committee_packet = CommitteePacket(
                portfolio_id=portfolio_snapshot.portfolio_id,
                as_of_date=portfolio_snapshot.as_of_date,
                base_currency=portfolio_config.base_currency,
                holdings=ordered_holdings,
                agent_outputs=[agent.dict() for agent in []],
                penalty_items=[],
                veto_logs=None,
            )
            decision_packet = DecisionPacket(
                portfolio_id=portfolio_snapshot.portfolio_id,
                as_of_date=portfolio_snapshot.as_of_date,
                base_currency=portfolio_config.base_currency,
                decision_summary={"status": "skeleton"},
            )
            hashes = compute_run_hashes(
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                committee_packet=committee_packet,
                decision_packet=decision_packet,
            )
            holding_packets = [state.to_packet() for state in holding_states]
            return self._build_completed_result(
                run_id=run_id,
                started_at=started_at,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                guard_results=guard_results,
                ordered_holdings=ordered_holdings,
                committee_packet=committee_packet,
                holding_packets=holding_packets,
                decision_packet=decision_packet,
                hashes=hashes,
            )

        if outcome == RunOutcome.SHORT_CIRCUITED:
            holding_packets = [state.to_packet() for state in holding_states]
            committee_packet = CommitteePacket(
                portfolio_id=portfolio_snapshot.portfolio_id,
                as_of_date=portfolio_snapshot.as_of_date,
                base_currency=portfolio_config.base_currency,
                holdings=ordered_holdings,
                agent_outputs=[],
                penalty_items=[],
                veto_logs=None,
            )
            return self._build_short_circuit_result(
                run_id=run_id,
                started_at=started_at,
                reasons=reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                guard_results=guard_results,
                ordered_holdings=ordered_holdings,
                committee_packet=committee_packet,
                holding_packets=holding_packets,
            )

        holding_packets = [state.to_packet() for state in holding_states if state.outcome != RunOutcome.COMPLETED]
        return self._build_failure_result(
            run_id=run_id,
            started_at=started_at,
            outcome=outcome,
            reasons=reasons,
            config_hashes=config_hashes,
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            guard_results=guard_results,
            ordered_holdings=ordered_holdings,
            holding_packets=holding_packets,
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
        holding_packets: Optional[List[HoldingPacket]] = None,
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
            outcome=outcome,
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
            holding_packets=holding_packets or [],
            ordered_holdings=ordered_holdings or [],
        )

    def _build_short_circuit_result(
        self,
        *,
        run_id: str,
        started_at: datetime,
        reasons: List[str],
        config_hashes: Dict[str, str],
        portfolio_snapshot: PortfolioSnapshot,
        portfolio_config: PortfolioConfig,
        run_config: RunConfig,
        guard_results: List[Any],
        ordered_holdings: List[Any],
        committee_packet: CommitteePacket,
        holding_packets: List[HoldingPacket],
    ) -> OrchestrationResult:
        ended_at = self._now_func()
        run_log = RunLog(
            run_id=run_id,
            started_at_utc=started_at,
            ended_at_utc=ended_at,
            status="terminal",
            outcome=RunOutcome.SHORT_CIRCUITED,
            reasons=reasons,
            config_hashes=config_hashes,
        )
        short_circuit_packet = ShortCircuitRunPacket(
            run_id=run_id,
            outcome=RunOutcome.SHORT_CIRCUITED,
            reasons=reasons,
            portfolio_id=portfolio_snapshot.portfolio_id,
            as_of_date=portfolio_snapshot.as_of_date,
            base_currency=portfolio_config.base_currency,
            run_mode=run_config.run_mode,
            committee_packet=committee_packet,
            holding_packets=holding_packets,
            config_hashes=config_hashes,
        )
        return OrchestrationResult(
            run_log=run_log,
            outcome=RunOutcome.SHORT_CIRCUITED,
            guard_results=guard_results,
            short_circuit_packet=short_circuit_packet,
            holding_packets=holding_packets,
            ordered_holdings=ordered_holdings,
        )

    def _build_completed_result(
        self,
        *,
        run_id: str,
        started_at: datetime,
        config_hashes: Dict[str, str],
        portfolio_snapshot: PortfolioSnapshot,
        portfolio_config: PortfolioConfig,
        run_config: RunConfig,
        guard_results: List[Any],
        ordered_holdings: List[Any],
        committee_packet: CommitteePacket,
        holding_packets: List[HoldingPacket],
        decision_packet: DecisionPacket,
        hashes: RunHashes,
    ) -> OrchestrationResult:
        ended_at = self._now_func()
        run_log = RunLog(
            run_id=run_id,
            started_at_utc=started_at,
            ended_at_utc=ended_at,
            status="terminal",
            outcome=RunOutcome.COMPLETED,
            reasons=[],
            config_hashes=config_hashes,
        )
        completed_run_packet = CompletedRunPacket(
            run_id=run_id,
            outcome=RunOutcome.COMPLETED,
            portfolio_id=portfolio_snapshot.portfolio_id,
            as_of_date=portfolio_snapshot.as_of_date,
            base_currency=portfolio_config.base_currency,
            run_mode=run_config.run_mode,
            committee_packet=committee_packet,
            holding_packets=holding_packets,
            decision_packet=decision_packet,
            hashes=HashBundle(**asdict(hashes)),
        )
        return OrchestrationResult(
            run_log=run_log,
            outcome=RunOutcome.COMPLETED,
            guard_results=guard_results,
            completed_run_packet=completed_run_packet,
            holding_packets=holding_packets,
            ordered_holdings=ordered_holdings,
        )

    @staticmethod
    def _format_error(error: Dict[str, Any]) -> str:
        location = ".".join(str(item) for item in error.get("loc", []))
        message = error.get("msg", "schema_validation_error")
        if location:
            return f"{location}:{message}"
        return message
