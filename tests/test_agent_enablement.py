from __future__ import annotations

import json
from pathlib import Path

from src.agents.base import BaseAgent
from src.agents.executor import HoldingAgentContext, run_holding_agents
from src.agents.registry import AgentRegistry, DEFAULT_AGENT_CLASSES
from src.core.guards.guards_g0_g10 import GuardContext, G5AgentConformanceGuard
from src.core.models import AgentResult, ConfigSnapshot, PortfolioConfig, PortfolioSnapshot, RunConfig, RunOutcome
from src.core.orchestration import Orchestrator
from src.core.utils.determinism import stable_sort_holdings


def _load_fixture(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("payload", payload)


def _base_inputs() -> dict:
    config_snapshot = _load_fixture("fixtures/config/ConfigSnapshot_v1.json")
    seeded = _load_fixture("fixtures/seeded/SeededData_HappyPath.json")
    return {
        "portfolio_snapshot_data": _load_fixture("fixtures/portfolio/PortfolioSnapshot_N3.json"),
        "portfolio_config_data": _load_fixture("fixtures/portfolio_config.json"),
        "run_config_data": _load_fixture("fixtures/config/RunConfig_DEEP.json"),
        "config_snapshot_data": {
            **config_snapshot,
            "registries": {
                **config_snapshot["registries"],
                **seeded,
            },
        },
        "manifest_data": None,
        "config_hashes": {
            "run_config_hash": "placeholder",
            "config_snapshot_hash": "placeholder",
        },
    }


def test_agent_execution_order_is_registry_defined():
    config_a = {
        "agents": {
            "Fundamentals": {"version": "0.1", "enabled": True},
            "Technical": {"version": "0.1", "enabled": True},
            "DevilsAdvocate": {"version": "0.1", "enabled": True},
        },
        "phases": {"ANALYTICAL": ["Fundamentals", "Technical", "DevilsAdvocate"]},
    }
    config_b = {
        "agents": {
            "DevilsAdvocate": {"version": "0.1", "enabled": True},
            "Technical": {"version": "0.1", "enabled": True},
            "Fundamentals": {"version": "0.1", "enabled": True},
        },
        "phases": {"ANALYTICAL": ["Fundamentals", "Technical", "DevilsAdvocate"]},
    }
    registry_a = AgentRegistry(config_data=config_a)
    registry_b = AgentRegistry(config_data=config_b)

    portfolio_snapshot = PortfolioSnapshot.parse_obj(_load_fixture("fixtures/portfolio/PortfolioSnapshot_N3.json"))
    ordered_holdings = stable_sort_holdings(portfolio_snapshot.holdings)
    holding = ordered_holdings[0]
    context = HoldingAgentContext(
        holding=holding,
        portfolio_snapshot=portfolio_snapshot,
        portfolio_config=PortfolioConfig.parse_obj(_load_fixture("fixtures/portfolio_config.json")),
        run_config=RunConfig.parse_obj(_load_fixture("fixtures/config/RunConfig_DEEP.json")),
        config_snapshot=ConfigSnapshot.parse_obj(_load_fixture("fixtures/config/ConfigSnapshot_v1.json")),
        ordered_holdings=ordered_holdings,
        agent_results=[],
    )

    results_a = run_holding_agents("ANALYTICAL", context, registry=registry_a)
    results_b = run_holding_agents("ANALYTICAL", context, registry=registry_b)

    assert [result.agent_name for result in results_a] == ["Fundamentals", "Technical", "DevilsAdvocate"]
    assert [result.agent_name for result in results_b] == ["Fundamentals", "Technical", "DevilsAdvocate"]


def test_agent_result_conformance_guard_fails_holding():
    portfolio_snapshot = PortfolioSnapshot.parse_obj(_load_fixture("fixtures/portfolio/PortfolioSnapshot_N3.json"))
    ordered_holdings = stable_sort_holdings(portfolio_snapshot.holdings)
    constructor = getattr(AgentResult, "model_construct", AgentResult.construct)
    agent_results = [
        constructor(
            agent_name="Fundamentals",
            scope="holding",
            status="invalid",
            confidence=0.5,
            key_findings={},
            metrics=[],
            suggested_penalties=[],
            veto_flags=[],
            holding_id=ordered_holdings[0].identity.holding_id,
        )
    ]
    context = GuardContext(
        portfolio_snapshot=portfolio_snapshot,
        portfolio_config=PortfolioConfig.parse_obj(_load_fixture("fixtures/portfolio_config.json")),
        run_config=RunConfig.parse_obj(_load_fixture("fixtures/config/RunConfig_DEEP.json")),
        config_snapshot=ConfigSnapshot.parse_obj(_load_fixture("fixtures/config/ConfigSnapshot_v1.json")),
        manifest=None,
        config_hashes={},
        ordered_holdings=ordered_holdings,
        agent_results=agent_results,
    )

    evaluation = G5AgentConformanceGuard().evaluate(context=context)

    assert evaluation.result.outcome is None
    assert evaluation.violations
    assert evaluation.violations[0].reason == "agent_schema_invalid"


def test_grra_short_circuit_blocks_non_governance_agents():
    inputs = _base_inputs()
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"] = {
        "GRRA": {"portfolio": {"do_not_trade_flag": True, "confidence": 1.0}}
    }

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.SHORT_CIRCUITED
    outputs = result.portfolio_committee_packet.agent_outputs
    agent_names = {item["agent_name"] for item in outputs}
    assert "Fundamentals" not in agent_names
    assert "Technical" not in agent_names
    assert "DevilsAdvocate" not in agent_names


def test_dio_veto_stops_downstream_for_holding():
    inputs = _base_inputs()
    inputs["run_config_data"] = {
        **inputs["run_config_data"],
        "partial_failure_veto_threshold_pct": 60.0,
    }
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"] = {
        "DIO": {"holdings": {"HOLDING-001": {"unsourced_numbers_detected": True, "confidence": 1.0}}}
    }

    result = Orchestrator().run(**inputs)

    holding_packet = next(packet for packet in result.holding_packets if packet.holding_id == "HOLDING-001")
    assert holding_packet.holding_run_outcome == RunOutcome.VETOED
    assert holding_packet.scorecard is None
    outputs = result.portfolio_committee_packet.agent_outputs
    vetoed_holdings = {item.get("holding_id") for item in outputs if item["agent_name"] == "DIO"}
    assert "HOLDING-001" in vetoed_holdings
    assert not any(
        item["agent_name"] != "DIO" and item.get("holding_id") == "HOLDING-001"
        for item in outputs
    )


def test_pscc_portfolio_output_available_before_aggregation():
    inputs = _base_inputs()
    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.COMPLETED
    outputs = result.portfolio_committee_packet.agent_outputs
    agent_order = [item["agent_name"] for item in outputs]
    assert "PSCC" in agent_order
    assert agent_order == sorted(agent_order)


def test_agent_result_conformance_guard_marks_holding_failed():
    class InvalidAgent(BaseAgent):
        @classmethod
        def supported_scopes(cls) -> set[str]:
            return {"holding"}

        def execute(self, context: HoldingAgentContext) -> AgentResult:
            holding_id = context.holding.identity.holding_id if context.holding.identity else None
            constructor = getattr(AgentResult, "model_construct", AgentResult.construct)
            if holding_id == "HOLDING-001":
                return constructor(
                    agent_name=self.agent_name,
                    scope="holding",
                    status="invalid",
                    confidence=0.5,
                    key_findings={},
                    metrics=[],
                    suggested_penalties=[],
                    veto_flags=[],
                    holding_id=holding_id,
                )
            return self._build_result(
                status="completed",
                confidence=0.5,
                key_findings={},
                metrics=[],
                holding_id=holding_id,
            )

    config_data = {
        "agents": {
            "DIO": {"version": "0.1", "enabled": True},
            "GRRA": {"version": "0.1", "enabled": True},
            "LEFO": {"version": "0.1", "enabled": True},
            "PSCC": {"version": "0.1", "enabled": True},
            "RiskOfficer": {"version": "0.1", "enabled": True},
            "InvalidAgent": {"version": "0.1", "enabled": True},
        },
        "phases": {
            "DIO": ["DIO"],
            "GRRA": ["GRRA"],
            "LEFO_PSCC": ["LEFO", "PSCC"],
            "RISK_OFFICER": ["RiskOfficer"],
            "ANALYTICAL": ["InvalidAgent"],
        },
    }
    registry = AgentRegistry(
        config_data=config_data,
        agent_classes={**DEFAULT_AGENT_CLASSES, "InvalidAgent": InvalidAgent},
    )
    inputs = _base_inputs()
    inputs["run_config_data"] = {
        **inputs["run_config_data"],
        "partial_failure_veto_threshold_pct": 60.0,
    }

    result = Orchestrator(registry=registry).run(**inputs)

    failed = next(packet for packet in result.holding_packets if packet.holding_id == "HOLDING-001")
    assert failed.holding_run_outcome == RunOutcome.FAILED


def test_agent_ordering_is_deterministic() -> None:
    inputs = _base_inputs()

    result_a = Orchestrator().run(**inputs)
    result_b = Orchestrator().run(**inputs)

    assert result_a.portfolio_committee_packet.agent_outputs == result_b.portfolio_committee_packet.agent_outputs
