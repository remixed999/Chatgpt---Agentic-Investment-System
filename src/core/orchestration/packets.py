from __future__ import annotations

from typing import List, Optional

from src.schemas.models import (
    FailedRunPacket,
    HoldingPacket,
    HoldingRunOutcome,
    PortfolioCommitteePacket,
    PortfolioRunOutcome,
)


def build_failed_packet(
    *,
    portfolio_id: str,
    outcome: PortfolioRunOutcome,
    reason: str,
    runlog_ref: str,
) -> FailedRunPacket:
    return FailedRunPacket(
        portfolio_id=portfolio_id,
        portfolio_run_outcome=outcome,
        reason=reason,
        runlog_ref=runlog_ref,
    )


def build_holding_packet(
    *,
    holding_id: str,
    outcome: HoldingRunOutcome,
    notes: Optional[str],
) -> HoldingPacket:
    return HoldingPacket(
        holding_id=holding_id,
        holding_run_outcome=outcome,
        notes=notes,
    )


def build_portfolio_packet(
    *,
    portfolio_id: str,
    outcome: PortfolioRunOutcome,
    holdings: List[HoldingPacket],
    runlog_ref: str,
) -> PortfolioCommitteePacket:
    return PortfolioCommitteePacket(
        portfolio_id=portfolio_id,
        portfolio_run_outcome=outcome,
        holdings=holdings,
        runlog_ref=runlog_ref,
    )
