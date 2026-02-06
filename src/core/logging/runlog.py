from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.schemas.models import RunLog, RunLogEvent


@dataclass
class RunLogBuilder:
    run_id: str
    started_at_utc: datetime
    events: List[RunLogEvent] = field(default_factory=list)

    def add_event(
        self,
        *,
        code: str,
        scope: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.events.append(
            RunLogEvent(
                code=code,
                scope=scope,
                message=message,
                details=details,
            )
        )

    def finish(self) -> RunLog:
        return RunLog(
            run_id=self.run_id,
            started_at_utc=self.started_at_utc,
            finished_at_utc=self.started_at_utc,
            events=self.events,
        )
