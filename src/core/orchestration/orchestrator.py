from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import ValidationError

from src.core.guards.registry import build_guard_registry
from src.core.models import (
    CommitteePacket,
    CompletedRunPacket,
    DecisionPacket,
    ConfigSnapshot,
    FailedRunPacket,
    HashBundle,
    OrchestrationResult,
    PortfolioConfig,
    PortfolioSnapshot,
    RunConfig,
    RunLog,
    RunOutcome,
)
from src.core.canonicalization.hashing import RunHashes, compute_run_hashes
from src.core.utils.determinism import stable_sort_holdings


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
        run_id: Optional[str] = None,
    ) -> OrchestrationResult:
        run_identifier = run_id or str(uuid4())
        started_at = self._now_func()
        guard_results = []

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

        g0_result = self._guards["G0"].evaluate(
            manifest=manifest_data,
            config_hashes=config_hashes,
        )
        guard_results.append(g0_result)
        if g0_result.outcome:
            return self._build_guard_failure(
                run_id=run_identifier,
                started_at=started_at,
                guard_results=guard_results,
                outcome=g0_result.outcome,
                reasons=g0_result.reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                ordered_holdings=ordered_holdings,
            )

        g1_result = self._guards["G1"].evaluate(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
        )
        guard_results.append(g1_result)
        if g1_result.outcome:
            return self._build_guard_failure(
                run_id=run_identifier,
                started_at=started_at,
                guard_results=guard_results,
                outcome=g1_result.outcome,
                reasons=g1_result.reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                ordered_holdings=ordered_holdings,
            )

        committee_packet = CommitteePacket(
            portfolio_id=portfolio_snapshot.portfolio_id,
            as_of_date=portfolio_snapshot.as_of_date,
            base_currency=portfolio_config.base_currency,
            holdings=ordered_holdings,
            agent_outputs=[],
            penalty_items=[],
            veto_logs=None,
        )
        decision_packet = DecisionPacket(
            portfolio_id=portfolio_snapshot.portfolio_id,
            as_of_date=portfolio_snapshot.as_of_date,
            base_currency=portfolio_config.base_currency,
            decision_summary={\"status\": \"skeleton\"},
        )

        hashes = compute_run_hashes(
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            committee_packet=committee_packet,
            decision_packet=decision_packet,
        )

        g7_result = self._guards[\"G7\"].evaluate(
            snapshot_hash=hashes.snapshot_hash,
            config_hash=hashes.config_hash,
            run_config_hash=hashes.run_config_hash,
            committee_packet_hash=hashes.committee_packet_hash,
            decision_hash=hashes.decision_hash,
            run_hash=hashes.run_hash,
        )
        guard_results.append(g7_result)
        if g7_result.outcome:
            return self._build_guard_failure(
                run_id=run_identifier,
                started_at=started_at,
                guard_results=guard_results,
                outcome=g7_result.outcome,
                reasons=g7_result.reasons,
                config_hashes=config_hashes,
                portfolio_snapshot=portfolio_snapshot,
                portfolio_config=portfolio_config,
                run_config=run_config,
                ordered_holdings=ordered_holdings,
            )

        return self._build_completed_result(
            run_id=run_identifier,
            started_at=started_at,
            config_hashes=config_hashes,
            portfolio_snapshot=portfolio_snapshot,
            portfolio_config=portfolio_config,
            run_config=run_config,
            guard_results=guard_results,
            ordered_holdings=ordered_holdings,
            committee_packet=committee_packet,
            decision_packet=decision_packet,
            hashes=hashes,
        )

    def _build_guard_failure(
        self,
        *,
        run_id: str,
        started_at: datetime,
        guard_results: List[Any],
        outcome: RunOutcome,
        reasons: List[str],
        config_hashes: Dict[str, str],
        portfolio_snapshot: PortfolioSnapshot,
        portfolio_config: PortfolioConfig,
        run_config: RunConfig,
        ordered_holdings: List[Any],
    ) -> OrchestrationResult:
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
            ordered_holdings=ordered_holdings or [],
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
        decision_packet: DecisionPacket,
        hashes: RunHashes,
    ) -> OrchestrationResult:
        ended_at = self._now_func()
        run_log = RunLog(
            run_id=run_id,
            started_at_utc=started_at,
            ended_at_utc=ended_at,
            status=\"terminal\",
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
            decision_packet=decision_packet,
            hashes=HashBundle(**asdict(hashes)),
        )
        return OrchestrationResult(
            run_log=run_log,
            outcome=RunOutcome.COMPLETED,
            guard_results=guard_results,
            completed_run_packet=completed_run_packet,
            ordered_holdings=ordered_holdings,
        )

    @staticmethod
    def _format_error(error: Dict[str, Any]) -> str:
        location = ".".join(str(item) for item in error.get("loc", []))
        message = error.get("msg", "schema_validation_error")
        if location:
            return f"{location}:{message}"
        return message
