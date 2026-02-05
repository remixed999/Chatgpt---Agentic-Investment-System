from __future__ import annotations

from typing import Any, Dict

from pydantic import ValidationError

from src.agents.base import BaseAgent
from src.core.models import AgentResult, MetricValue
from src.core.penalties import DIOOutput


class DIOAgent(BaseAgent):
    @classmethod
    def supported_scopes(cls) -> set[str]:
        return {"portfolio", "holding"}

    def execute(self, context: Any) -> AgentResult:
        holding_id = getattr(context, "holding", None)
        holding_id_value = holding_id.identity.holding_id if holding_id and holding_id.identity else None
        seed = self._seed(context, holding_id_value)
        payload = {
            "staleness_flags": seed.get("staleness_flags", []),
            "missing_hard_stop_fields": seed.get("missing_hard_stop_fields", []),
            "missing_penalty_critical_fields": seed.get("missing_penalty_critical_fields", []),
            "contradictions": seed.get("contradictions", []),
            "unsourced_numbers_detected": seed.get("unsourced_numbers_detected", False),
            "corporate_action_risk": seed.get("corporate_action_risk"),
            "low_source_reliability": seed.get("low_source_reliability", False),
            "integrity_veto_triggered": seed.get("integrity_veto_triggered", False),
        }
        try:
            dio_output = DIOOutput.parse_obj(payload)
            key_findings = dio_output.dict()
        except ValidationError:
            key_findings = DIOOutput().dict()
        confidence = float(seed.get("confidence", 1.0))
        return self._build_result(
            status="completed",
            confidence=confidence,
            key_findings=key_findings,
            metrics=self._parse_metrics(seed),
            holding_id=holding_id_value,
        )

    @staticmethod
    def _seed(context: Any, holding_id: str | None) -> Dict[str, Any]:
        registries = getattr(context, "config_snapshot").registries or {}
        fixtures = registries.get("agent_fixtures", {})
        agent_fixture = fixtures.get("DIO", {})
        if holding_id:
            return agent_fixture.get("holdings", {}).get(holding_id, {})
        return agent_fixture.get("portfolio", agent_fixture)

    @staticmethod
    def _parse_metrics(seed: Dict[str, Any]) -> list[MetricValue]:
        raw_metrics = seed.get("metrics", [])
        return [MetricValue.parse_obj(metric) for metric in raw_metrics]
