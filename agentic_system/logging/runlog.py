from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional, Tuple

from agentic_system.schemas.contracts import ConfigSnapshot


# DD-01/DD-02: RunLog structure only
@dataclass(frozen=True)
class AgentExecutionRecord:
    agent_name: str
    start_time: datetime
    end_time: datetime
    status: str
    output_summary: Mapping[str, Any]
    holding_id: Optional[str] = None


@dataclass(frozen=True)
class ErrorRecord:
    timestamp: datetime
    error_type: str
    error_message: str
    holding_id: Optional[str] = None
    agent_name: Optional[str] = None
    traceback: Optional[str] = None


@dataclass(frozen=True)
class RunLog:
    run_id: str
    portfolio_run_outcome: str
    per_holding_outcomes: Mapping[str, str]
    run_mode: str
    config_snapshot: ConfigSnapshot
    input_snapshot_hash: str
    agent_execution_log: Tuple[AgentExecutionRecord, ...]
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    errors: Tuple[ErrorRecord, ...]
    canonical_output_hash: Optional[str] = None
