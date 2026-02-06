from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from pydantic import ValidationError

from src.aggregation import HoldingState
from src.core.guards.base import GuardScope, GuardViolation
from src.core.models import AgentResult, HoldingInput, RunConfig, RunOutcome
from src.core.penalties import DIOOutput


@dataclass(frozen=True)
class GovernanceDecision:
    portfolio_outcome: RunOutcome
    portfolio_reasons: List[str]
    holding_states: List[HoldingState]

    def with_portfolio_override(self, outcome: RunOutcome, reasons: List[str]) -> GovernanceDecision:
        merged_reasons = list(self.portfolio_reasons)
        for reason in reasons:
            if reason not in merged_reasons:
                merged_reasons.append(reason)
        return GovernanceDecision(
            portfolio_outcome=outcome,
            portfolio_reasons=merged_reasons,
            holding_states=self.holding_states,
        )


class GovernanceEngine:
    def evaluate(
        self,
        *,
        ordered_holdings: List[HoldingInput],
        agent_results: List[AgentResult],
        guard_results: Iterable,
        guard_violations: List[GuardViolation],
        run_config: RunConfig,
    ) -> GovernanceDecision:
        holding_states = self._initialize_holdings(ordered_holdings)
        holding_ids = [self._holding_id_for(index, holding) for index, holding in enumerate(ordered_holdings)]
        holding_reasons = {holding_id: [] for holding_id in holding_ids}
        holding_outcomes = {holding_id: RunOutcome.COMPLETED for holding_id in holding_ids}

        for violation in guard_violations:
            if violation.scope != GuardScope.HOLDING:
                continue
            holding_id = violation.holding_id or ""
            if not holding_id and violation.holding_index is not None and violation.holding_index < len(holding_ids):
                holding_id = holding_ids[violation.holding_index]
            holding_reasons.setdefault(holding_id, []).append(violation.reason)
            if violation.outcome == RunOutcome.FAILED:
                holding_outcomes[holding_id] = RunOutcome.FAILED
            elif holding_outcomes.get(holding_id) != RunOutcome.FAILED:
                holding_outcomes[holding_id] = violation.outcome

        portfolio_reasons: List[str] = []
        portfolio_outcome = RunOutcome.COMPLETED

        if self._dio_guard_vetoed(guard_results) or self._dio_portfolio_veto(agent_results):
            portfolio_outcome = RunOutcome.VETOED
            portfolio_reasons.append("dio_portfolio_veto")

        if portfolio_outcome == RunOutcome.COMPLETED and self._grra_short_circuit(agent_results, run_config):
            portfolio_outcome = RunOutcome.SHORT_CIRCUITED
            portfolio_reasons.append("grra_do_not_trade")

        for holding_id, vetoed in self._dio_holding_vetoes(agent_results).items():
            if not vetoed:
                continue
            if holding_outcomes.get(holding_id) != RunOutcome.FAILED:
                holding_outcomes[holding_id] = RunOutcome.VETOED
                holding_reasons.setdefault(holding_id, []).append("dio_integrity_veto")

        for holding_id in self._risk_officer_vetoes(agent_results):
            if holding_outcomes.get(holding_id) == RunOutcome.COMPLETED:
                holding_outcomes[holding_id] = RunOutcome.VETOED
                holding_reasons.setdefault(holding_id, []).append("risk_officer_veto")

        if portfolio_outcome == RunOutcome.SHORT_CIRCUITED:
            for holding_id in holding_outcomes.keys():
                holding_outcomes[holding_id] = RunOutcome.SHORT_CIRCUITED

        updated_states: List[HoldingState] = []
        for index, state in enumerate(holding_states):
            holding_id = holding_ids[index]
            updated_states.append(
                HoldingState(
                    holding=state.holding,
                    outcome=holding_outcomes.get(holding_id, state.outcome),
                    reasons=holding_reasons.get(holding_id, []),
                )
            )

        return GovernanceDecision(
            portfolio_outcome=portfolio_outcome,
            portfolio_reasons=portfolio_reasons,
            holding_states=updated_states,
        )

    @staticmethod
    def _initialize_holdings(ordered_holdings: List[HoldingInput]) -> List[HoldingState]:
        holding_states: List[HoldingState] = []
        for index, holding in enumerate(ordered_holdings):
            holding_states.append(HoldingState(holding=holding, outcome=RunOutcome.COMPLETED, reasons=[]))
        return holding_states

    @staticmethod
    def _holding_id_for(index: int, holding: HoldingInput) -> str:
        if holding.identity and holding.identity.holding_id:
            return holding.identity.holding_id
        return f"holding_index_{index}"

    @staticmethod
    def _dio_guard_vetoed(guard_results: Iterable) -> bool:
        for result in guard_results:
            if getattr(result, "guard_id", "") in {"G1", "G2", "G3", "G4"} and result.outcome == RunOutcome.VETOED:
                return True
        return False

    @staticmethod
    def _dio_portfolio_veto(agent_results: Iterable[AgentResult]) -> bool:
        for agent in agent_results:
            if agent.agent_name != "DIO" or agent.scope != "portfolio":
                continue
            if GovernanceEngine._dio_output_veto(agent.key_findings):
                return True
        return False

    @staticmethod
    def _dio_holding_vetoes(agent_results: Iterable[AgentResult]) -> Dict[str, bool]:
        vetoes: Dict[str, bool] = {}
        for agent in agent_results:
            if agent.agent_name != "DIO" or agent.scope != "holding":
                continue
            holding_id = agent.holding_id or ""
            vetoes[holding_id] = GovernanceEngine._dio_output_veto(agent.key_findings)
        return vetoes

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
    def _risk_officer_vetoes(agent_results: Iterable[AgentResult]) -> List[str]:
        vetoed: List[str] = []
        for agent in agent_results:
            if agent.agent_name != "RiskOfficer" or agent.scope != "holding":
                continue
            if agent.veto_flags:
                vetoed.append(agent.holding_id or "")
        return vetoed
