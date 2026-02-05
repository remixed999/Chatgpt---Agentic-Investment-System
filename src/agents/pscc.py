from __future__ import annotations

from typing import Any, Dict

from src.agents.base import BaseAgent
from src.core.models import MetricValue


class PSCCAgent(BaseAgent):
    @classmethod
    def supported_scopes(cls) -> set[str]:
        return {"portfolio"}

    def execute(self, context: Any):
        seed = self._seed(context)
        key_findings: Dict[str, Any] = {
            "concentration_breaches": seed.get("concentration_breaches", []),
            "position_caps_applied": seed.get("position_caps_applied", []),
            "fx_exposure_by_currency": seed.get("fx_exposure_by_currency", {}),
            "portfolio_liquidity_risk": seed.get("portfolio_liquidity_risk", []),
        }
        if "fx_exposure_reports" in seed:
            key_findings["fx_exposure_reports"] = seed["fx_exposure_reports"]
        confidence = float(seed.get("confidence", 0.0))
        return self._build_result(
            status="completed",
            confidence=confidence,
            key_findings=key_findings,
            metrics=self._parse_metrics(seed),
        )

    @staticmethod
    def _seed(context: Any) -> Dict[str, Any]:
        registries = getattr(context, "config_snapshot").registries or {}
        fixtures = registries.get("agent_fixtures", {})
        agent_fixture = fixtures.get("PSCC", {})
        return agent_fixture.get("portfolio", agent_fixture)

    @staticmethod
    def _parse_metrics(seed: Dict[str, Any]) -> list[MetricValue]:
        raw_metrics = seed.get("metrics", [])
        return [MetricValue.parse_obj(metric) for metric in raw_metrics]
