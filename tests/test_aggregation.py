from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from src.core.canonicalization import canonical_json_dumps
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


def test_tf01_happy_path_emits_hashes_and_expected_packet():
    inputs = _base_inputs()

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.COMPLETED
    packet = result.portfolio_committee_packet
    assert packet is not None
    assert packet.run_hash is not None

    expected = _load_fixture("fixtures/expected/TF-01_expected_portfolio_packet.json")
    assert canonical_json_dumps(packet.model_dump()) == canonical_json_dumps(expected)


def test_dio_veto_excludes_penalties_and_scores():
    inputs = _base_inputs()
    inputs["run_config_data"] = {**inputs["run_config_data"], "partial_failure_veto_threshold_pct": 60.0}
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"]["DIO"]["holdings"][
        "HOLDING-001"
    ] = {
        "missing_hard_stop_fields": ["cash"],
        "confidence": 1.0,
    }

    result = Orchestrator().run(**inputs)

    holding_packet = next(packet for packet in result.holding_packets if packet.holding_id == "HOLDING-001")
    assert holding_packet.holding_run_outcome == RunOutcome.VETOED
    assert holding_packet.scorecard is None


def test_tf03_grra_short_circuit_no_hashes():
    inputs = _base_inputs()
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"]["GRRA"]["portfolio"] = {
        "do_not_trade_flag": True,
        "confidence": 1.0,
    }

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.SHORT_CIRCUITED
    packet = result.portfolio_committee_packet
    assert packet is not None
    assert packet.run_hash is None
    assert all(holding.holding_run_outcome == RunOutcome.SHORT_CIRCUITED for holding in packet.holdings)

    expected = _load_fixture("fixtures/expected/TF-03_expected_short_circuit.json")
    assert canonical_json_dumps(packet.model_dump()) == canonical_json_dumps(expected)


def test_tf05_burn_rate_veto_emits_minimal_packet():
    inputs = _base_inputs()
    inputs["run_config_data"] = {**inputs["run_config_data"], "partial_failure_veto_threshold_pct": 60.0}
    inputs["run_config_data"]["burn_rate_classification"]["HOLDING-002"] = True
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"]["DIO"]["holdings"]["HOLDING-002"] = {
        "missing_hard_stop_fields": ["cash"],
        "confidence": 1.0,
    }

    result = Orchestrator().run(**inputs)

    holding_packet = next(packet for packet in result.holding_packets if packet.holding_id == "HOLDING-002")
    assert holding_packet.holding_run_outcome == RunOutcome.VETOED
    assert holding_packet.scorecard is None

    expected = _load_fixture("fixtures/expected/TF-05_expected_burn_rate_veto.json")
    assert canonical_json_dumps(result.portfolio_committee_packet.model_dump()) == canonical_json_dumps(expected)


def test_deterministic_ordering_for_holdings_and_penalties():
    inputs = _base_inputs()
    snapshot = inputs["portfolio_snapshot_data"]
    reversed_snapshot = {**snapshot, "holdings": list(reversed(snapshot["holdings"]))}

    penalty_fixture = {
        "missing_penalty_critical_fields": [
            {"field_name": "cash", "not_applicable": False},
            {"field_name": "price", "not_applicable": False},
        ],
        "staleness_flags": [
            {"staleness_type": "price_volume", "age_days": 10, "hard_stop_triggered": False}
        ],
        "confidence": 0.9,
    }
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"]["DIO"]["holdings"][
        "HOLDING-002"
    ] = penalty_fixture

    inputs_a = {**inputs, "portfolio_snapshot_data": snapshot}
    inputs_b = {**inputs, "portfolio_snapshot_data": reversed_snapshot}

    result_a = Orchestrator().run(**inputs_a)
    result_b = Orchestrator().run(**inputs_b)

    holdings_a = [packet.holding_id for packet in result_a.holding_packets]
    holdings_b = [packet.holding_id for packet in result_b.holding_packets]
    assert holdings_a == sorted(holdings_a)
    assert holdings_a == holdings_b

    target_a = next(packet for packet in result_a.holding_packets if packet.holding_id == "HOLDING-002")
    target_b = next(packet for packet in result_b.holding_packets if packet.holding_id == "HOLDING-002")
    details_a = target_a.scorecard.penalty_breakdown.details
    details_b = target_b.scorecard.penalty_breakdown.details
    assert details_a == details_b
    assert details_a == sorted(details_a, key=lambda item: (item.category, item.reason, item.source_agent))


def test_tf12_penalty_caps_enforced_for_deep_and_fast():
    inputs = _base_inputs()
    inputs["config_snapshot_data"]["registries"]["agent_fixtures"]["DIO"]["holdings"][
        "HOLDING-003"
    ] = {
        "missing_penalty_critical_fields": [
            {"field_name": "cash", "not_applicable": False},
            {"field_name": "price", "not_applicable": False},
            {"field_name": "macro_regime_input", "not_applicable": False}
        ],
        "staleness_flags": [
            {"staleness_type": "financials", "age_days": 200, "hard_stop_triggered": False},
            {"staleness_type": "price_volume", "age_days": 10, "hard_stop_triggered": False}
        ],
        "contradictions": [{"unresolved": False}],
        "corporate_action_risk": {"split_days_ago": 30, "dividend_days_ago": 45},
        "confidence": 0.9,
    }

    result_deep = Orchestrator().run(**inputs)
    holding = next(packet for packet in result_deep.holding_packets if packet.holding_id == "HOLDING-003")
    assert holding.scorecard.penalty_breakdown.total_penalties == -35.0
    assert "penalty_cap_applied" in holding.scorecard.notes

    fast_inputs = deepcopy(inputs)
    fast_inputs["run_config_data"] = {**fast_inputs["run_config_data"], "run_mode": "FAST"}
    result_fast = Orchestrator().run(**fast_inputs)
    holding_fast = next(packet for packet in result_fast.holding_packets if packet.holding_id == "HOLDING-003")
    assert holding_fast.scorecard.penalty_breakdown.total_penalties >= -40.0
    assert "penalty_cap_applied" not in holding_fast.scorecard.notes

    expected = _load_fixture("fixtures/expected/TF-12_expected_penalty_cap.json")
    assert canonical_json_dumps(result_deep.portfolio_committee_packet.model_dump()) == canonical_json_dumps(expected)


def test_tf13_canonical_hash_stability():
    inputs = _base_inputs()
    snapshot = inputs["portfolio_snapshot_data"]
    reordered = {**snapshot, "holdings": list(reversed(snapshot["holdings"]))}

    result_a = Orchestrator().run(**inputs)
    inputs["portfolio_snapshot_data"] = reordered
    result_b = Orchestrator().run(**inputs)

    assert result_a.outcome == RunOutcome.COMPLETED
    assert result_b.outcome == RunOutcome.COMPLETED
    assert result_a.portfolio_committee_packet.run_hash == result_b.portfolio_committee_packet.run_hash

    expected = _load_fixture("fixtures/expected/TF-13_expected_canonical_hash_stability.json")
    assert canonical_json_dumps(result_a.portfolio_committee_packet.model_dump()) == canonical_json_dumps(expected)


def test_tf14_partial_failure_threshold_boundary():
    inputs = _base_inputs()
    snapshot = deepcopy(inputs["portfolio_snapshot_data"])
    snapshot["holdings"] = snapshot["holdings"][:2]
    snapshot["holdings"][0]["identity"] = None

    inputs["portfolio_snapshot_data"] = snapshot
    inputs_equal = deepcopy(inputs)
    inputs_equal["run_config_data"] = {"run_mode": "FAST", "partial_failure_veto_threshold_pct": 50.0}
    result_equal = Orchestrator().run(**inputs_equal)
    assert result_equal.outcome == RunOutcome.COMPLETED

    inputs_above = deepcopy(inputs)
    inputs_above["run_config_data"] = {"run_mode": "FAST", "partial_failure_veto_threshold_pct": 49.0}
    result_above = Orchestrator().run(**inputs_above)
    assert result_above.outcome == RunOutcome.VETOED

    expected = _load_fixture("fixtures/expected/TF-14_expected_partial_failure_threshold.json")
    assert canonical_json_dumps(result_equal.portfolio_committee_packet.model_dump()) == canonical_json_dumps(expected)


def test_tf15_failed_run_emits_failed_packet_only():
    inputs = _base_inputs()
    inputs["portfolio_snapshot_data"] = _load_fixture(
        "fixtures/portfolio/PortfolioSnapshot_TF15_invalid.json"
    )

    result = Orchestrator().run(**inputs)

    assert result.outcome == RunOutcome.FAILED
    assert result.portfolio_committee_packet is None
    expected = _load_fixture("fixtures/expected/TF-15_expected_failed_packet.json")
    assert result.failed_run_packet is not None
    assert canonical_json_dumps(result.failed_run_packet.model_dump()) == canonical_json_dumps(expected)
