from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, root_validator


class StrictBaseModel(BaseModel):
    class Config:
        extra = "forbid"


class RunMode(str, Enum):
    FAST = "FAST"
    DEEP = "DEEP"


class RunOutcome(str, Enum):
    FAILED = "FAILED"
    VETOED = "VETOED"
    SHORT_CIRCUITED = "SHORT_CIRCUITED"
    COMPLETED = "COMPLETED"


class HoldingIdentity(StrictBaseModel):
    holding_id: Optional[str] = None
    ticker: Optional[str] = None
    identifier: Optional[str] = None


class SourceRef(StrictBaseModel):
    origin: str
    as_of_date: datetime
    retrieval_timestamp: datetime


class MetricValue(StrictBaseModel):
    value: Optional[float] = None
    source_ref: Optional[SourceRef] = None
    missing_reason: Optional[str] = None
    not_applicable: bool = False

    @root_validator
    def validate_semantics(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        value = values.get("value")
        missing_reason = values.get("missing_reason")
        not_applicable = values.get("not_applicable")
        if value is None and not not_applicable and missing_reason is None:
            raise ValueError("MetricValue missing_reason required when value is None and not_applicable is False")
        if not_applicable and missing_reason is not None:
            raise ValueError("MetricValue missing_reason must be None when not_applicable is True")
        return values


class HoldingInput(StrictBaseModel):
    identity: Optional[HoldingIdentity] = None
    weight: float
    currency: Optional[str] = None
    metrics: Dict[str, MetricValue] = Field(default_factory=dict)


class PortfolioSnapshot(StrictBaseModel):
    portfolio_id: str
    as_of_date: datetime
    holdings: List[HoldingInput]
    cash_pct: Optional[float] = None
    retrieval_timestamp: Optional[datetime] = None


class PortfolioConfig(StrictBaseModel):
    base_currency: Optional[str] = None
    retrieval_timestamp: Optional[datetime] = None


class RunConfig(StrictBaseModel):
    run_mode: RunMode
    partial_failure_veto_threshold_pct: float = 30.0
    debug_mode: bool = False
    do_not_trade_flag: bool = False
    retrieval_timestamp: Optional[datetime] = None
    staleness_thresholds: Dict[str, Any] = Field(default_factory=dict)
    penalty_caps: Dict[str, Any] = Field(default_factory=dict)
    burn_rate_classification: Dict[str, bool] = Field(default_factory=dict)


class ConfigSnapshot(StrictBaseModel):
    rubric_version: str
    registries: Dict[str, Any] = Field(default_factory=dict)
    hash: str


class AgentResult(StrictBaseModel):
    agent_name: str
    scope: str
    status: str
    output: Dict[str, Any] = Field(default_factory=dict)
    holding_id: Optional[str] = None
    confidence: Optional[float] = None


class PenaltyItem(StrictBaseModel):
    category: str
    reason: str
    amount: float
    source_agent: str


class PenaltyBreakdown(StrictBaseModel):
    category_A_missing_critical: float
    category_B_staleness: float
    category_C_contradictions_integrity: float
    category_D_confidence: float
    category_E_fx_exposure_risk: float
    category_F_data_validity: float
    total_penalties: float
    details: List[PenaltyItem] = Field(default_factory=list)


class Scorecard(StrictBaseModel):
    base_score: Optional[float] = None
    final_score: Optional[float] = None
    penalty_breakdown: Optional[PenaltyBreakdown] = None


class RunLog(StrictBaseModel):
    run_id: str
    started_at_utc: datetime
    ended_at_utc: datetime
    status: str
    outcome: RunOutcome
    reasons: List[str]
    config_hashes: Dict[str, str]


class FailedRunPacket(StrictBaseModel):
    run_id: str
    outcome: RunOutcome
    reasons: List[str]
    portfolio_id: Optional[str] = None
    as_of_date: Optional[datetime] = None
    base_currency: Optional[str] = None
    run_mode: Optional[RunMode] = None
    config_hashes: Dict[str, str] = Field(default_factory=dict)


class CommitteePacket(StrictBaseModel):
    portfolio_id: str
    as_of_date: datetime
    base_currency: Optional[str] = None
    holdings: List[HoldingInput] = Field(default_factory=list)
    agent_outputs: List[Dict[str, Any]] = Field(default_factory=list)
    penalty_items: List[Dict[str, Any]] = Field(default_factory=list)
    veto_logs: Optional[List[Dict[str, Any]]] = None
    generated_at: Optional[datetime] = None


class DecisionPacket(StrictBaseModel):
    portfolio_id: str
    as_of_date: datetime
    base_currency: Optional[str] = None
    decision_summary: Dict[str, Any] = Field(default_factory=dict)
    limitations: Optional[str] = None
    generated_at: Optional[datetime] = None


class HashBundle(StrictBaseModel):
    snapshot_hash: str
    config_hash: str
    run_config_hash: str
    committee_packet_hash: str
    decision_hash: str
    run_hash: str


class HoldingPacket(StrictBaseModel):
    holding_id: Optional[str] = None
    outcome: RunOutcome
    reasons: List[str] = Field(default_factory=list)
    identity: Optional[HoldingIdentity] = None
    scorecard: Optional[Scorecard] = None


class CompletedRunPacket(StrictBaseModel):
    run_id: str
    outcome: RunOutcome
    portfolio_id: str
    as_of_date: datetime
    base_currency: Optional[str] = None
    run_mode: Optional[RunMode] = None
    committee_packet: CommitteePacket
    holding_packets: List[HoldingPacket] = Field(default_factory=list)
    decision_packet: DecisionPacket
    hashes: HashBundle


class ShortCircuitRunPacket(StrictBaseModel):
    run_id: str
    outcome: RunOutcome
    reasons: List[str]
    portfolio_id: Optional[str] = None
    as_of_date: Optional[datetime] = None
    base_currency: Optional[str] = None
    run_mode: Optional[RunMode] = None
    committee_packet: Optional[CommitteePacket] = None
    holding_packets: List[HoldingPacket] = Field(default_factory=list)
    config_hashes: Dict[str, str] = Field(default_factory=dict)


class GuardResult(StrictBaseModel):
    guard_id: str
    status: str
    outcome: Optional[RunOutcome] = None
    reasons: List[str] = Field(default_factory=list)


class OrchestrationResult(StrictBaseModel):
    run_log: RunLog
    outcome: RunOutcome
    guard_results: List[GuardResult]
    failed_run_packet: Optional[FailedRunPacket] = None
    completed_run_packet: Optional[CompletedRunPacket] = None
    short_circuit_packet: Optional[ShortCircuitRunPacket] = None
    holding_packets: List[HoldingPacket] = Field(default_factory=list)
    ordered_holdings: List[HoldingInput] = Field(default_factory=list)
