from __future__ import annotations

from typing import Any, Dict

from src.agents.base import BaseAgent
from src.core.models import MetricValue


class DevilsAdvocateAgent(BaseAgent):
    @classmethod
    def supported_scopes(cls) -> set[str]:
        return {"holding"}

    def execute(self, context: Any):
        holding = context.holding
        holding_id = holding.identity.holding_id if holding.identity else None
        seed = self._seed(context, holding_id)
        unresolved_fatal_risk = bool(seed.get("unresolved_fatal_risk", False))
        key_findings: Dict[str, Any] = {
            "risk_flags": seed.get("risk_flags", []),
            "unresolved_fatal_risk": unresolved_fatal_risk,
            "narrative_limitations": seed.get("narrative_limitations", ""),
        }
        confidence = float(seed.get("confidence", 0.0))
        counter_case = seed.get("counter_case")
        return self._build_result(
            status="completed",
            confidence=confidence,
            key_findings=key_findings,
            metrics=self._parse_metrics(seed),
            counter_case=counter_case,
            holding_id=holding_id,
        )

    @staticmethod
    def _seed(context: Any, holding_id: str | None) -> Dict[str, Any]:
        registries = getattr(context, "config_snapshot").registries or {}
        fixtures = registries.get("agent_fixtures", {})
        agent_fixture = fixtures.get("DevilsAdvocate", {})
        if holding_id:
            return agent_fixture.get("holdings", {}).get(holding_id, {})
        return agent_fixture

    @staticmethod
    def _parse_metrics(seed: Dict[str, Any]) -> list[MetricValue]:
        raw_metrics = seed.get("metrics", [])
        return [MetricValue.parse_obj(metric) for metric in raw_metrics]
