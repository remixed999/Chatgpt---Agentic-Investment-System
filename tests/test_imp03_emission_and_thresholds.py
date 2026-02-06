from __future__ import annotations

import json
from pathlib import Path

from src.core.models import RunOutcome
from src.core.orchestration import Orchestrator


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


def test_emission_completed_includes_hashes_and_holding_packets() -> None:
    result = Orchestrator().run(**_base_inputs())

    assert result.outcome == RunOutcome.COMPLETED
    assert result.failed_run_packet is None
    assert result.portfolio_committee_packet is not None
    assert result.portfolio_committee_packet.run_hash is not None
    assert result.holding_packets


def test_failed_emits_failed_packet_only() -> None:
    inputs = _base_inputs()
    inputs["portfolio_snapshot_data"] = {"as_of_date": "2024-01-01T00:00:00+00:00", "holdings": []}

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.FAILED
    assert result.failed_run_packet is not None
    assert result.portfolio_committee_packet is None


def test_provenance_guard_vetoes_unsourced_numeric_metrics() -> None:
    inputs = _base_inputs()
    inputs["portfolio_snapshot_data"]["holdings"][0]["metrics"] = {"pe_ratio": {"value": 10.0}}

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.VETOED
    assert result.portfolio_committee_packet is not None


def test_partial_failure_threshold_strictly_greater_than() -> None:
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
