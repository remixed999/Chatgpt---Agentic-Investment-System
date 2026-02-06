from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class StrictBaseModel(BaseModel):
    model_config = {
        "extra": "forbid",
        "populate_by_name": True,
        "validate_by_name": True,
    }


class SourceRef(StrictBaseModel):
    origin: Optional[str] = None
    as_of_date: datetime
    retrieval_timestamp: datetime


class MetricValue(StrictBaseModel):
    value: Optional[float] = None
    source_ref: Optional[SourceRef] = None
    missing_reason: Optional[str] = None
    not_applicable: bool = False


class HoldingIdentity(StrictBaseModel):
    holding_id: Optional[str] = None
    ticker: Optional[str] = None
    identifier: Optional[str] = None


class HoldingInput(StrictBaseModel):
    identity: Optional[HoldingIdentity] = None
    weight: float
    currency: Optional[str] = None
    metrics: Dict[str, MetricValue] = Field(default_factory=dict)


class PortfolioSnapshot(StrictBaseModel):
    portfolio_id: str
    as_of_date: str
    holdings: List[HoldingInput]
    cash_pct: float
    retrieval_timestamp: Optional[str] = None


class PortfolioConfig(StrictBaseModel):
    base_currency: Optional[str] = None


class RunConfig(StrictBaseModel):
    run_mode: Literal["FAST", "DEEP"]
    partial_failure_veto_threshold_pct: float = 30.0


class ConfigSnapshot(StrictBaseModel):
    rubric_version: str
    hard_stop_field_registry: Dict[str, Any] = Field(default_factory=dict)
    penalty_critical_field_registry: Dict[str, Any] = Field(default_factory=dict)


class PortfolioRunOutcome(str, Enum):
    COMPLETED = "COMPLETED"
    VETOED = "VETOED"
    FAILED = "FAILED"
    SHORT_CIRCUITED = "SHORT_CIRCUITED"


class HoldingRunOutcome(str, Enum):
    COMPLETED = "COMPLETED"
    VETOED = "VETOED"
    FAILED = "FAILED"
    SHORT_CIRCUITED = "SHORT_CIRCUITED"


class FailedRunPacket(StrictBaseModel):
    portfolio_id: str
    portfolio_run_outcome: PortfolioRunOutcome
    reason: str
    runlog_ref: str


class HoldingPacket(StrictBaseModel):
    holding_id: str
    holding_run_outcome: HoldingRunOutcome
    notes: Optional[str] = None


class PortfolioCommitteePacket(StrictBaseModel):
    portfolio_id: str
    portfolio_run_outcome: PortfolioRunOutcome
    holdings: List[HoldingPacket]
    runlog_ref: str


class RunLogEvent(StrictBaseModel):
    code: str
    scope: str
    message: str
    details: Optional[Dict[str, Any]] = None


class RunLog(StrictBaseModel):
    run_id: str
    started_at_utc: datetime
    finished_at_utc: datetime
    events: List[RunLogEvent]


class OrchestrationResult(StrictBaseModel):
    run_log: RunLog
    packet: FailedRunPacket | PortfolioCommitteePacket
