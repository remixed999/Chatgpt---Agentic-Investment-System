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


def test_missing_base_currency_vetoes_portfolio_and_omits_hashes():
    inputs = _base_inputs()
    inputs["portfolio_config_data"] = {"base_currency": None}

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.VETOED
    assert result.failed_run_packet is None
    assert result.portfolio_committee_packet is not None


def test_missing_holding_identity_marks_holding_failed_and_allows_completion():
    inputs = _base_inputs()
    inputs["run_config_data"] = {"run_mode": "FAST", "partial_failure_veto_threshold_pct": 60.0}
    inputs["portfolio_snapshot_data"]["holdings"][0]["identity"] = None

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.COMPLETED
    assert result.portfolio_committee_packet is not None
    failed_packets = [packet for packet in result.holding_packets if packet.holding_run_outcome == RunOutcome.FAILED]
    assert len(failed_packets) == 1


def test_unsourced_numeric_metric_triggers_dio_veto():
    inputs = _base_inputs()
    inputs["portfolio_snapshot_data"]["holdings"][0]["metrics"] = {"pe_ratio": {"value": 10.0}}

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.VETOED
    assert result.portfolio_committee_packet is not None


def test_partial_failure_threshold_strict_comparison():
    inputs_equal = _base_inputs()
    inputs_equal["portfolio_snapshot_data"]["holdings"] = inputs_equal["portfolio_snapshot_data"]["holdings"][:2]
    inputs_equal["run_config_data"] = {"run_mode": "FAST", "partial_failure_veto_threshold_pct": 50.0}
    inputs_equal["portfolio_snapshot_data"]["holdings"][0]["identity"] = None
    result_equal = Orchestrator().run(**inputs_equal)

    assert result_equal.outcome == RunOutcome.COMPLETED

    inputs_above = _base_inputs()
    inputs_above["portfolio_snapshot_data"]["holdings"] = inputs_above["portfolio_snapshot_data"]["holdings"][:2]
    inputs_above["run_config_data"] = {"run_mode": "FAST", "partial_failure_veto_threshold_pct": 49.0}
    inputs_above["portfolio_snapshot_data"]["holdings"][0]["identity"] = None
    result_above = Orchestrator().run(**inputs_above)

    assert result_above.outcome == RunOutcome.VETOED


def test_grra_short_circuit_forces_portfolio_and_holdings_short_circuited():
    inputs = _base_inputs()
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"] = {
        "GRRA": {"portfolio": {"do_not_trade_flag": True, "confidence": 1.0}}
    }

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.SHORT_CIRCUITED
    assert result.portfolio_committee_packet is not None
    assert all(packet.holding_run_outcome == RunOutcome.SHORT_CIRCUITED for packet in result.holding_packets)


def test_emission_eligibility_by_outcome():
    completed = Orchestrator().run(**_base_inputs())

    assert completed.outcome == RunOutcome.COMPLETED
    assert completed.portfolio_committee_packet is not None
    assert completed.portfolio_committee_packet.run_hash is not None
    assert completed.holding_packets

    vetoed_inputs = _base_inputs()
    vetoed_inputs["portfolio_config_data"] = {"base_currency": None}
    vetoed = Orchestrator().run(**vetoed_inputs)

    assert vetoed.outcome == RunOutcome.VETOED
    assert vetoed.failed_run_packet is None
    assert vetoed.portfolio_committee_packet is not None

    failed_inputs = _base_inputs()
    failed_inputs["portfolio_snapshot_data"] = {"as_of_date": "2024-01-01T00:00:00+00:00", "holdings": []}
    failed = Orchestrator().run(**failed_inputs)

    assert failed.outcome == RunOutcome.FAILED
    assert failed.portfolio_committee_packet is None
    assert failed.failed_run_packet is not None

    short_inputs = _base_inputs()
    short_inputs["config_snapshot_data"]["registries"]["agent_fixtures"] = {
        "GRRA": {"portfolio": {"do_not_trade_flag": True, "confidence": 1.0}}
    }
    shorted = Orchestrator().run(**short_inputs)

    assert shorted.outcome == RunOutcome.SHORT_CIRCUITED
    assert shorted.portfolio_committee_packet is not None
