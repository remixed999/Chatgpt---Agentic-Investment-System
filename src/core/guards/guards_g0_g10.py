from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.core.guards.base import (
    Guard,
    GuardEvaluation,
    GuardScope,
    GuardViolation,
    fail_result,
    pass_result,
)
from src.core.models import (
    AgentResult,
    ConfigSnapshot,
    HoldingInput,
    PortfolioConfig,
    PortfolioSnapshot,
    RunConfig,
    RunOutcome,
)


@dataclass
class GuardContext:
    portfolio_snapshot: PortfolioSnapshot
    portfolio_config: PortfolioConfig
    run_config: RunConfig
    config_snapshot: ConfigSnapshot
    manifest: Optional[Dict[str, str]]
    config_hashes: Dict[str, str]
    ordered_holdings: List[HoldingInput]
    agent_results: List[AgentResult]
    portfolio_outcome: Optional[RunOutcome] = None


class G0InputSchemaGuard(Guard):
    guard_id = "G0"

    def evaluate(self, *, context: GuardContext) -> GuardEvaluation:
        manifest = context.manifest
        if manifest is None:
            return GuardEvaluation(result=pass_result(self.guard_id))

        missing_keys = [
            key
            for key in ("run_config_hash", "config_snapshot_hash")
            if key not in manifest
        ]
        if missing_keys:
            reasons = [f"manifest_missing_{key}" for key in missing_keys]
            return GuardEvaluation(result=fail_result(self.guard_id, RunOutcome.FAILED, reasons))

        mismatches = []
        if manifest.get("run_config_hash") != context.config_hashes.get("run_config_hash"):
            mismatches.append("run_config_hash_mismatch")
        if manifest.get("config_snapshot_hash") != context.config_hashes.get("config_snapshot_hash"):
            mismatches.append("config_snapshot_hash_mismatch")

        if mismatches:
            return GuardEvaluation(result=fail_result(self.guard_id, RunOutcome.FAILED, mismatches))

        return GuardEvaluation(result=pass_result(self.guard_id))


class G1IdentityContextGuard(Guard):
    guard_id = "G1"

    def evaluate(self, *, context: GuardContext) -> GuardEvaluation:
        violations: List[GuardViolation] = []
        if context.portfolio_snapshot and not context.portfolio_config.base_currency:
            return GuardEvaluation(
                result=fail_result(self.guard_id, RunOutcome.VETOED, ["missing_base_currency"]),
                violations=violations,
            )

        for index, holding in enumerate(context.ordered_holdings):
            identity = holding.identity
            if identity is None or not identity.holding_id or not (identity.ticker or identity.identifier):
                violations.append(
                    GuardViolation(
                        scope=GuardScope.HOLDING,
                        outcome=RunOutcome.FAILED,
                        reason="holding_identity_missing",
                        holding_id=identity.holding_id if identity else None,
                        holding_index=index,
                    )
                )

        return GuardEvaluation(
            result=pass_result(self.guard_id),
            violations=violations,
        )


class G2ProvenanceGuard(Guard):
    guard_id = "G2"

    def evaluate(self, *, context: GuardContext) -> GuardEvaluation:
        for holding in context.ordered_holdings:
            for metric in holding.metrics.values():
                if metric.value is not None and not metric.not_applicable and metric.source_ref is None:
                    return GuardEvaluation(
                        result=fail_result(self.guard_id, RunOutcome.VETOED, ["unsourced_numeric_metric"]),
                    )
        return GuardEvaluation(result=pass_result(self.guard_id))


class G3FreshnessGuard(Guard):
    guard_id = "G3"

    def evaluate(self, *, context: GuardContext) -> GuardEvaluation:
        return GuardEvaluation(result=pass_result(self.guard_id))


class G4RegistryCompletenessGuard(Guard):
    guard_id = "G4"

    def evaluate(self, *, context: GuardContext) -> GuardEvaluation:
        if context.config_snapshot.registries is None:
            return GuardEvaluation(
                result=fail_result(self.guard_id, RunOutcome.FAILED, ["missing_registries"]),
            )
        return GuardEvaluation(result=pass_result(self.guard_id))


class G5AgentConformanceGuard(Guard):
    guard_id = "G5"

    def evaluate(self, *, context: GuardContext) -> GuardEvaluation:
        violations: List[GuardViolation] = []
        for agent in context.agent_results:
            if agent.scope not in {"portfolio", "holding"}:
                return GuardEvaluation(
                    result=fail_result(self.guard_id, RunOutcome.FAILED, ["agent_scope_invalid"]),
                )
            if agent.status not in {"completed", "failed", "skipped"}:
                return GuardEvaluation(
                    result=fail_result(self.guard_id, RunOutcome.FAILED, ["agent_status_invalid"]),
                )
            if agent.scope == "holding" and not agent.holding_id:
                violations.append(
                    GuardViolation(
                        scope=GuardScope.HOLDING,
                        outcome=RunOutcome.FAILED,
                        reason="agent_missing_holding_id",
                    )
                )
        return GuardEvaluation(result=pass_result(self.guard_id), violations=violations)


class G6GovernancePrecedenceGuard(Guard):
    guard_id = "G6"

    def evaluate(self, *, context: GuardContext) -> GuardEvaluation:
        if context.portfolio_outcome in {RunOutcome.FAILED, RunOutcome.VETOED}:
            return GuardEvaluation(result=pass_result(self.guard_id))

        for agent in context.agent_results:
            if agent.agent_name == "GRRA" and agent.output.get("do_not_trade_flag") is True:
                return GuardEvaluation(
                    result=fail_result(self.guard_id, RunOutcome.SHORT_CIRCUITED, ["grra_do_not_trade"]),
                )

        if context.run_config.do_not_trade_flag:
            return GuardEvaluation(
                result=fail_result(self.guard_id, RunOutcome.SHORT_CIRCUITED, ["grra_do_not_trade"]),
            )
        return GuardEvaluation(result=pass_result(self.guard_id))


class G7DeterminismGuard(Guard):
    guard_id = "G7"

    def evaluate(self, *, context: GuardContext) -> GuardEvaluation:
        holding_ids = [
            holding.identity.holding_id
            for holding in context.ordered_holdings
            if holding.identity and holding.identity.holding_id
        ]
        if holding_ids != sorted(holding_ids):
            return GuardEvaluation(
                result=fail_result(self.guard_id, RunOutcome.FAILED, ["determinism_order_violation"]),
            )
        return GuardEvaluation(result=pass_result(self.guard_id))


class G8EmissionEligibilityGuard(Guard):
    guard_id = "G8"

    def evaluate(self, *, context: GuardContext) -> GuardEvaluation:
        return GuardEvaluation(result=pass_result(self.guard_id))


class G9PartialFailureGuard(Guard):
    guard_id = "G9"

    def evaluate(
        self,
        *,
        context: GuardContext,
        holding_outcomes: List[RunOutcome],
    ) -> GuardEvaluation:
        total_holdings = len(holding_outcomes)
        if total_holdings == 0:
            return GuardEvaluation(
                result=fail_result(self.guard_id, RunOutcome.FAILED, ["no_holdings_provided"]),
            )
        failure_or_veto_count = sum(
            1 for outcome in holding_outcomes if outcome in {RunOutcome.FAILED, RunOutcome.VETOED}
        )
        failure_rate_pct = (failure_or_veto_count / total_holdings) * 100.0
        if failure_rate_pct > context.run_config.partial_failure_veto_threshold_pct:
            return GuardEvaluation(
                result=fail_result(self.guard_id, RunOutcome.VETOED, ["partial_failure_threshold_exceeded"]),
            )
        return GuardEvaluation(result=pass_result(self.guard_id))


class G10ArtifactCompletenessGuard(Guard):
    guard_id = "G10"

    def evaluate(self, *, context: GuardContext) -> GuardEvaluation:
        return GuardEvaluation(result=pass_result(self.guard_id))
