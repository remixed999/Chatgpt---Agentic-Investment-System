from __future__ import annotations

from typing import Any, Dict

from src.agents.base import BaseAgent
from src.core.models import MetricValue


class GRRAAgent(BaseAgent):
    @classmethod
    def supported_scopes(cls) -> set[str]:
        return {"portfolio"}

    def execute(self, context: Any):
        seed = self._seed(context)
        regime_label = seed.get("regime_label", "unknown")
        if seed.get("regime_label") is None:
            regime_label = "unknown"
        key_findings = {
            "regime_label": regime_label,
            "regime_confidence": seed.get("regime_confidence"),
            "do_not_trade_flag": seed.get("do_not_trade_flag", False),
        }
        if seed.get("regime_label") is None:
            key_findings["missing_reason"] = "macro_regime_input_missing"
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
        agent_fixture = fixtures.get("GRRA", {})
        return agent_fixture.get("portfolio", agent_fixture)

    @staticmethod
    def _parse_metrics(seed: Dict[str, Any]) -> list[MetricValue]:
        raw_metrics = seed.get("metrics", [])
        return [MetricValue.parse_obj(metric) for metric in raw_metrics]
