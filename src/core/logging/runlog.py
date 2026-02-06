from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from src.core.models import RunLog, RunOutcome


@dataclass
class RunLogBuilder:
    run_id: str
    started_at_utc: datetime
    config_hashes: Dict[str, str] = field(default_factory=dict)
    outcome: RunOutcome = RunOutcome.COMPLETED
    status: str = "in_progress"
    reasons: List[str] = field(default_factory=list)

    def add_reason(self, reason: str) -> None:
        if reason and reason not in self.reasons:
            self.reasons.append(reason)

    def extend_reasons(self, reasons: List[str]) -> None:
        for reason in reasons:
            self.add_reason(reason)

    def set_outcome(self, outcome: RunOutcome, *, status: Optional[str] = None) -> None:
        self.outcome = outcome
        if status is not None:
            self.status = status

    def finish(self) -> RunLog:
        return RunLog(
            run_id=self.run_id,
            started_at_utc=self.started_at_utc,
            ended_at_utc=self.started_at_utc,
            status=self.status,
            outcome=self.outcome,
            reasons=self.reasons,
            config_hashes=self.config_hashes,
        )
