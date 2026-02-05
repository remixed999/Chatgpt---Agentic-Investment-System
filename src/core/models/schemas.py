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
    holding_id: str
    ticker: Optional[str] = None
    identifier: Optional[str] = None

    @root_validator
    def ensure_identifier_present(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        ticker = values.get("ticker")
        identifier = values.get("identifier")
        if not ticker and not identifier:
            raise ValueError("HoldingIdentity requires ticker or identifier")
        return values


class HoldingInput(StrictBaseModel):
    identity: HoldingIdentity
    weight: float
    currency: Optional[str] = None


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
    retrieval_timestamp: Optional[datetime] = None


class ConfigSnapshot(StrictBaseModel):
    rubric_version: str
    registries: Dict[str, Any] = Field(default_factory=dict)
    hash: str


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


class CompletedRunPacket(StrictBaseModel):
    run_id: str
    outcome: RunOutcome
    portfolio_id: str
    as_of_date: datetime
    base_currency: Optional[str] = None
    run_mode: Optional[RunMode] = None
    committee_packet: CommitteePacket
    decision_packet: DecisionPacket
    hashes: HashBundle


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
    ordered_holdings: List[HoldingInput] = Field(default_factory=list)
