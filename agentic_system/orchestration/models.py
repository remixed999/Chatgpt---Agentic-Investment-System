from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Optional, Sequence

from agentic_system.schemas.contracts import (
    AgentResult,
    ConfigSnapshot,
    DIOOutput,
    GRRAOutput,
    HoldingPacket,
    PortfolioCommitteePacket,
    PortfolioConfig,
    PortfolioSnapshot,
    RunConfig,
)


@dataclass(frozen=True)
class HoldingEvaluationInput:
    holding_id: str
    agent_results: Sequence[AgentResult]
    dio_output: Optional[DIOOutput] = None
    lefo_output: Optional[AgentResult] = None


@dataclass(frozen=True)
class PortfolioEvaluationInput:
    grra_output: Optional[GRRAOutput] = None
    pscc_output: Optional[AgentResult] = None
    risk_officer_output: Optional[AgentResult] = None


@dataclass(frozen=True)
class RunInputs:
    run_id: str
    snapshot: PortfolioSnapshot
    config: PortfolioConfig
    run_config: RunConfig
    config_snapshot: ConfigSnapshot
    holdings: Mapping[str, HoldingEvaluationInput]
    portfolio: PortfolioEvaluationInput
    started_at: datetime


@dataclass(frozen=True)
class RunResult:
    portfolio_outcome: str
    holding_packets: Sequence[HoldingPacket]
    committee_packet: Optional[PortfolioCommitteePacket]
    errors: Sequence[str] = field(default_factory=tuple)

