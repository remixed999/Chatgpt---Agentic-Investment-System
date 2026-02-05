from __future__ import annotations

from typing import Any, Dict

from src.agents.base import BaseAgent
from src.core.models import MetricValue


class TechnicalAgent(BaseAgent):
    @classmethod
    def supported_scopes(cls) -> set[str]:
        return {"holding"}

    def execute(self, context: Any):
        holding = context.holding
        holding_id = holding.identity.holding_id if holding.identity else None
        seed = self._seed(context, holding_id)
        key_findings: Dict[str, Any] = {
            "technical_signals": seed.get("technical_signals", {}),
        }
        confidence = float(seed.get("confidence", 0.0))
        return self._build_result(
            status="completed",
            confidence=confidence,
            key_findings=key_findings,
            metrics=self._parse_metrics(seed),
            holding_id=holding_id,
        )

    @staticmethod
    def _seed(context: Any, holding_id: str | None) -> Dict[str, Any]:
        registries = getattr(context, "config_snapshot").registries or {}
        fixtures = registries.get("agent_fixtures", {})
        agent_fixture = fixtures.get("Technical", {})
        if holding_id:
            return agent_fixture.get("holdings", {}).get(holding_id, {})
        return agent_fixture

    @staticmethod
    def _parse_metrics(seed: Dict[str, Any]) -> list[MetricValue]:
        raw_metrics = seed.get("metrics", [])
        return [MetricValue.parse_obj(metric) for metric in raw_metrics]
