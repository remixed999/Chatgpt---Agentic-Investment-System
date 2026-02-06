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


class PortfolioSnapshot(StrictBaseModel):
    portfolio_id: str
    as_of_date: str
    holdings: List["HoldingInput"]


class HoldingInput(StrictBaseModel):
    holding_id: str
    identifier: Optional[str] = None
    weight: Optional[float] = None


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
