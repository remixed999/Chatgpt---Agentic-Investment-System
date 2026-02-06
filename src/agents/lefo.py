from __future__ import annotations

from typing import Any, Dict

from src.agents.base import BaseAgent
from src.core.models import MetricValue


class LEFOAgent(BaseAgent):
    @classmethod
    def supported_scopes(cls) -> set[str]:
        return {"holding"}

    def execute(self, context: Any):
        holding = context.holding
        holding_id = holding.identity.holding_id if holding.identity else None
        seed = self._seed(context, holding_id)
        key_findings: Dict[str, Any] = {
            "liquidity_grade": seed.get("liquidity_grade", "unknown"),
            "exit_risk_warnings": seed.get("exit_risk_warnings", []),
            "hard_override_triggered": seed.get("hard_override_triggered", False),
        }
        if "score_cap" in seed:
            key_findings["score_cap"] = seed["score_cap"]
        if "max_score" in seed:
            key_findings["max_score"] = seed["max_score"]
        if "max_position_cap_pct" in seed:
            key_findings["max_position_cap_pct"] = seed["max_position_cap_pct"]
        if "time_to_exit_estimate" in seed:
            key_findings["time_to_exit_estimate"] = seed["time_to_exit_estimate"]
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
        agent_fixture = fixtures.get("LEFO", {})
        if holding_id:
            return agent_fixture.get("holdings", {}).get(holding_id, {})
        return agent_fixture

    @staticmethod
    def _parse_metrics(seed: Dict[str, Any]) -> list[MetricValue]:
        raw_metrics = seed.get("metrics", [])
        return [MetricValue.parse_obj(metric) for metric in raw_metrics]
