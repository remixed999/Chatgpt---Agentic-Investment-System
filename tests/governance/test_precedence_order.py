from __future__ import annotations

import json
from pathlib import Path

from src.core.models import RunOutcome
from src.core.orchestration import Orchestrator


def _load_fixture(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("payload", payload)


def _base_inputs():
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


def test_dio_portfolio_veto_blocks_scoring_and_caps() -> None:
    inputs = _base_inputs()
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"] = {
        "DIO": {"portfolio": {"integrity_veto_triggered": True}}
    }

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.VETOED
    assert result.portfolio_committee_packet is not None
    assert result.portfolio_committee_packet.run_hash is None
    assert result.holding_packets == []


def test_grra_short_circuit_prevents_penalties_and_caps() -> None:
    inputs = _base_inputs()
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"] = {
        "GRRA": {"portfolio": {"do_not_trade_flag": True, "confidence": 1.0}}
    }

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.SHORT_CIRCUITED
    for packet in result.holding_packets:
        assert packet.holding_run_outcome == RunOutcome.SHORT_CIRCUITED
        assert packet.scorecard is None


def test_risk_officer_veto_skips_penalties_and_caps() -> None:
    inputs = _base_inputs()
    inputs["run_config_data"] = {"run_mode": "FAST", "partial_failure_veto_threshold_pct": 60.0}
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"] = {
        "RiskOfficer": {"holdings": {"HOLDING-002": {"veto_flags": ["risk_veto"]}}}
    }

    result = Orchestrator().run(**inputs)

    vetoed = next(packet for packet in result.holding_packets if packet.holding_id == "HOLDING-002")
    assert vetoed.holding_run_outcome == RunOutcome.VETOED
    assert vetoed.scorecard is None


def test_caps_applied_before_penalties() -> None:
    inputs = _base_inputs()
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"] = {
        "DIO": {
            "holdings": {
                "HOLDING-001": {
                    "missing_penalty_critical_fields": [
                        {"field_name": "shares_outstanding", "not_applicable": False}
                    ]
                }
            }
        },
        "LEFO": {"holdings": {"HOLDING-001": {"score_cap": 60.0, "confidence": 1.0}}},
        "PSCC": {
            "portfolio": {
                "position_caps_applied": [{"holding_id": "HOLDING-001", "score_cap": 70.0}],
                "confidence": 1.0,
            }
        },
    }

    result = Orchestrator().run(**inputs)
    holding = next(packet for packet in result.holding_packets if packet.holding_id == "HOLDING-001")

    assert holding.scorecard is not None
    assert holding.scorecard.base_score == 60.0
    assert holding.scorecard.penalty_breakdown.total_penalties < 0.0
    assert holding.scorecard.final_score == 60.0 + holding.scorecard.penalty_breakdown.total_penalties


def test_penalties_not_applied_to_dio_vetoed_holding() -> None:
    inputs = _base_inputs()
    inputs["run_config_data"] = {"run_mode": "FAST", "partial_failure_veto_threshold_pct": 60.0}
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"] = {
        "DIO": {"holdings": {"HOLDING-003": {"integrity_veto_triggered": True}}}
    }

    result = Orchestrator().run(**inputs)
    vetoed = next(packet for packet in result.holding_packets if packet.holding_id == "HOLDING-003")

    assert vetoed.holding_run_outcome == RunOutcome.VETOED
    assert vetoed.scorecard is None
