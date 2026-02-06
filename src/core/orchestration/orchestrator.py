from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from src.core.logging.runlog import RunLogBuilder
from src.core.orchestration.outcomes import HoldingRunOutcome, PortfolioRunOutcome
from src.core.orchestration.packets import build_failed_packet, build_holding_packet, build_portfolio_packet
from src.core.validation.schema_gate import ValidationResult, validate_or_raise
from src.schemas.models import HoldingPacket, OrchestrationResult


DEFAULT_RUN_ID = "local-run"
DEFAULT_TIME = datetime(2025, 1, 1, tzinfo=timezone.utc)


class Orchestrator:
    def __init__(self, now_func: Optional[Callable[[], datetime]] = None) -> None:
        self._now_func = now_func or (lambda: DEFAULT_TIME)

    def run(
        self,
        *,
        portfolio_snapshot_data: Dict[str, object],
        portfolio_config_data: Dict[str, object],
        run_config_data: Dict[str, object],
        config_snapshot_data: Dict[str, object],
        run_id: Optional[str] = None,
    ) -> OrchestrationResult:
        run_identifier = run_id or DEFAULT_RUN_ID
        started_at = self._now_func()
        runlog = RunLogBuilder(run_id=run_identifier, started_at_utc=started_at)

        validation = validate_or_raise(
            portfolio_snapshot_data=portfolio_snapshot_data,
            portfolio_config_data=portfolio_config_data,
            run_config_data=run_config_data,
            config_snapshot_data=config_snapshot_data,
        )

        if validation.portfolio_failed:
            runlog.add_event(
                code="intake_validation_fail",
                scope="portfolio",
                message="Schema validation failed.",
                details={"errors": validation.portfolio_errors},
            )
            packet = build_failed_packet(
                portfolio_id=validation.portfolio_id or "UNKNOWN",
                outcome=PortfolioRunOutcome.FAILED,
                reason="schema_validation_failed",
                runlog_ref=run_identifier,
            )
            return OrchestrationResult(run_log=runlog.finish(), packet=packet)

        if validation.portfolio_errors or validation.holding_errors:
            runlog.add_event(
                code="intake_validation_fail",
                scope="portfolio",
                message="Contract validation found issues.",
                details={"portfolio_errors": validation.portfolio_errors, "holding_errors": validation.holding_errors},
            )
        else:
            runlog.add_event(
                code="intake_validation_pass",
                scope="portfolio",
                message="Contract validation passed.",
            )

        holding_packets = self._build_holding_packets(validation, runlog)
        portfolio_outcome = self._determine_portfolio_outcome(validation, holding_packets, runlog)

        runlog.add_event(
            code="final_outcome",
            scope="portfolio",
            message=f"Portfolio outcome: {portfolio_outcome.value}.",
            details={"portfolio_outcome": portfolio_outcome.value},
        )

        runlog_entry = runlog.finish()
        if portfolio_outcome == PortfolioRunOutcome.COMPLETED:
            packet = build_portfolio_packet(
                portfolio_id=validation.portfolio_id or "UNKNOWN",
                outcome=portfolio_outcome,
                holdings=holding_packets,
                runlog_ref=run_identifier,
            )
        else:
            packet = build_failed_packet(
                portfolio_id=validation.portfolio_id or "UNKNOWN",
                outcome=portfolio_outcome,
                reason="portfolio_vetoed",
                runlog_ref=run_identifier,
            )

        return OrchestrationResult(run_log=runlog_entry, packet=packet)

    def _build_holding_packets(
        self, validation: ValidationResult, runlog: RunLogBuilder
    ) -> List[HoldingPacket]:
        holding_packets: List[HoldingPacket] = []
        seen_ids = set()

        for holding in validation.valid_holdings:
            holding_id = holding.holding_id
            seen_ids.add(holding_id)
            if holding_id in validation.holding_errors:
                runlog.add_event(
                    code="holding_failed_identity",
                    scope="holding",
                    message="Holding identity failed validation.",
                    details={"holding_id": holding_id},
                )
                holding_packets.append(
                    build_holding_packet(
                        holding_id=holding_id,
                        outcome=HoldingRunOutcome.FAILED,
                        notes="holding_identity_missing",
                    )
                )
            else:
                holding_packets.append(
                    build_holding_packet(
                        holding_id=holding_id,
                        outcome=HoldingRunOutcome.COMPLETED,
                        notes=None,
                    )
                )

        for holding_id, issues in sorted(validation.holding_errors.items()):
            if holding_id in seen_ids:
                continue
            runlog.add_event(
                code="holding_failed_identity",
                scope="holding",
                message="Holding identity failed validation.",
                details={"holding_id": holding_id, "errors": issues},
            )
            holding_packets.append(
                build_holding_packet(
                    holding_id=holding_id,
                    outcome=HoldingRunOutcome.FAILED,
                    notes="holding_identity_missing",
                )
            )

        return holding_packets

    def _determine_portfolio_outcome(
        self,
        validation: ValidationResult,
        holding_packets: List[HoldingPacket],
        runlog: RunLogBuilder,
    ) -> PortfolioRunOutcome:
        if validation.portfolio_vetoed:
            runlog.add_event(
                code="portfolio_veto_base_currency",
                scope="portfolio",
                message="Portfolio base currency missing.",
            )
            return PortfolioRunOutcome.VETOED

        total_holdings = len(holding_packets)
        failed_holdings = sum(
            1 for packet in holding_packets if packet.holding_run_outcome == HoldingRunOutcome.FAILED
        )
        failure_rate_pct = (failed_holdings / total_holdings * 100.0) if total_holdings else 0.0
        threshold = (
            validation.run_config.partial_failure_veto_threshold_pct
            if validation.run_config
            else 0.0
        )
        if failure_rate_pct > threshold:
            runlog.add_event(
                code="portfolio_partial_failure_veto",
                scope="portfolio",
                message="Partial failure rate exceeded veto threshold.",
                details={
                    "failure_rate_pct": failure_rate_pct,
                    "threshold_pct": threshold,
                },
            )
            return PortfolioRunOutcome.VETOED

        return PortfolioRunOutcome.COMPLETED
