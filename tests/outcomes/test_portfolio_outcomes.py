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


def test_tf01_happy_path_completed() -> None:
    result = Orchestrator().run(**_base_inputs())

    assert result.outcome == RunOutcome.COMPLETED
    assert result.portfolio_committee_packet is not None
    assert result.portfolio_committee_packet.run_hash is not None


def test_tf02_missing_base_currency_vetoed() -> None:
    inputs = _base_inputs()
    inputs["portfolio_config_data"] = {"base_currency": None}

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.VETOED
    assert result.portfolio_committee_packet is not None


def test_tf03_grra_short_circuited() -> None:
    inputs = _base_inputs()
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"] = {
        "GRRA": {"portfolio": {"do_not_trade_flag": True, "confidence": 1.0}}
    }

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.SHORT_CIRCUITED
    assert all(packet.holding_run_outcome == RunOutcome.SHORT_CIRCUITED for packet in result.holding_packets)


def test_tf04_identity_missing_holding_failed() -> None:
    inputs = _base_inputs()
    inputs["portfolio_snapshot_data"] = _load_fixture(
        "fixtures/portfolio/PortfolioSnapshot_TF04_identity_missing.json"
    )
    inputs["run_config_data"] = {"run_mode": "FAST", "partial_failure_veto_threshold_pct": 60.0}

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.COMPLETED
    failed = next(packet for packet in result.holding_packets if packet.holding_run_outcome == RunOutcome.FAILED)
    assert any("error_classification:holding_identity_missing" in note for note in failed.limitations)


def test_tf14_partial_failure_threshold_strict_greater_than() -> None:
    inputs = _base_inputs()
    inputs["portfolio_snapshot_data"] = _load_fixture(
        "fixtures/portfolio/PortfolioSnapshot_TF14_partial_failure.json"
    )
    inputs["run_config_data"] = _load_fixture("fixtures/config/RunConfig_TF14.json")

    result_equal = Orchestrator().run(**inputs)

    assert result_equal.outcome == RunOutcome.COMPLETED

    inputs_above = _base_inputs()
    inputs_above["portfolio_snapshot_data"] = _load_fixture(
        "fixtures/portfolio/PortfolioSnapshot_TF14_partial_failure.json"
    )
    inputs_above["run_config_data"] = {"run_mode": "FAST", "partial_failure_veto_threshold_pct": 49.0}
    result_above = Orchestrator().run(**inputs_above)

    assert result_above.outcome == RunOutcome.VETOED
