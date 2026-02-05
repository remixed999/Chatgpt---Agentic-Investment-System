from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.core.models import AgentResult, MetricValue, PenaltyItem


@dataclass(frozen=True)
class BaseAgent:
    agent_name: str
    agent_version: str
    scope: str

    def execute(self, context: Any) -> AgentResult:
        raise NotImplementedError

    @classmethod
    def supported_scopes(cls) -> set[str]:
        return {"portfolio", "holding"}

    def _build_result(
        self,
        *,
        status: str,
        confidence: float,
        key_findings: Optional[Dict[str, Any]] = None,
        metrics: Optional[List[MetricValue]] = None,
        suggested_penalties: Optional[List[PenaltyItem]] = None,
        veto_flags: Optional[List[str]] = None,
        counter_case: Optional[str] = None,
        notes: Optional[str] = None,
        holding_id: Optional[str] = None,
    ) -> AgentResult:
        return AgentResult(
            agent_name=self.agent_name,
            scope=self.scope,
            status=status,
            confidence=confidence,
            key_findings=key_findings or {},
            metrics=metrics or [],
            suggested_penalties=suggested_penalties or [],
            veto_flags=veto_flags or [],
            counter_case=counter_case,
            notes=notes,
            holding_id=holding_id,
        )
