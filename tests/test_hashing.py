from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.core.canonicalization import (
    canonical_json_dumps,
    hash_portfolio_config,
    hash_portfolio_snapshot,
    hash_run_config,
    hash_run_hash,
    replay_hashes_ignore_timestamps,
    replay_hashes_match,
)
from src.core.models import PortfolioConfig, PortfolioSnapshot, RunConfig
from src.core.orchestration import Orchestrator
from src.core.models import RunOutcome


FIXED_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)


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


def test_snapshot_hash_stable_for_holdings_order():
    snapshot_a = PortfolioSnapshot.parse_obj(_load_fixture("fixtures/portfolio_snapshot_order_a.json"))
    snapshot_b = PortfolioSnapshot.parse_obj(_load_fixture("fixtures/portfolio_snapshot_order_b.json"))

    assert hash_portfolio_snapshot(snapshot_a) == hash_portfolio_snapshot(snapshot_b)
    assert replay_hashes_match(snapshot_a, snapshot_b)


def test_timestamp_exclusion_keeps_hashes_stable():
    snapshot_a = PortfolioSnapshot.parse_obj(
        {
            **_load_fixture("fixtures/portfolio_snapshot_order_a.json"),
            "retrieval_timestamp": "2024-01-01T00:00:00+00:00",
        }
    )
    snapshot_b = PortfolioSnapshot.parse_obj(
        {
            **_load_fixture("fixtures/portfolio_snapshot_order_a.json"),
            "retrieval_timestamp": "2024-01-02T00:00:00+00:00",
        }
    )
    config_a = PortfolioConfig.parse_obj({"base_currency": "USD", "retrieval_timestamp": "2024-01-01T00:00:00+00:00"})
    config_b = PortfolioConfig.parse_obj({"base_currency": "USD", "retrieval_timestamp": "2024-01-02T00:00:00+00:00"})
    run_config_a = RunConfig.parse_obj({"run_mode": "FAST", "retrieval_timestamp": "2024-01-01T00:00:00+00:00"})
    run_config_b = RunConfig.parse_obj({"run_mode": "FAST", "retrieval_timestamp": "2024-01-02T00:00:00+00:00"})

    assert hash_portfolio_snapshot(snapshot_a) == hash_portfolio_snapshot(snapshot_b)
    assert hash_portfolio_config(config_a) == hash_portfolio_config(config_b)
    assert hash_run_config(run_config_a) == hash_run_config(run_config_b)
    assert replay_hashes_ignore_timestamps(snapshot_a, snapshot_b)


def test_hash_gating_skips_failed_and_vetoed_runs():
    inputs = _base_inputs()
    inputs["portfolio_config_data"] = {"base_currency": None}

    orchestrator = Orchestrator(now_func=lambda: FIXED_TIME)
    result = orchestrator.run(**inputs)

    assert result.outcome == RunOutcome.VETOED
    assert result.portfolio_committee_packet is not None
    assert result.portfolio_committee_packet.run_hash is None
    assert result.portfolio_committee_packet.decision_hash is None


def test_hash_gating_emits_hashes_for_completed_runs():
    inputs = _base_inputs()

    result = Orchestrator(now_func=lambda: FIXED_TIME).run(**inputs)

    assert result.outcome == RunOutcome.COMPLETED
    packet = result.portfolio_committee_packet
    assert packet is not None
    assert packet.snapshot_hash is not None
    assert packet.config_hash is not None
    assert packet.run_config_hash is not None
    assert packet.committee_packet_hash is not None
    assert packet.decision_hash is not None
    assert packet.run_hash is not None


def test_hash_gating_skips_failed_runs():
    inputs = _base_inputs()
    inputs["portfolio_snapshot_data"] = {
        "as_of_date": "2024-01-01T00:00:00+00:00",
        "holdings": [],
    }

    result = Orchestrator(now_func=lambda: FIXED_TIME).run(**inputs)

    assert result.outcome == RunOutcome.FAILED
    assert result.portfolio_committee_packet is None


def test_numeric_formatting_is_canonical():
    payload = {
        "small": 1e-6,
        "trail": 1.2300,
        "whole": 2.0,
    }

    encoded = canonical_json_dumps(payload)

    assert "0.000001" in encoded
    assert "1.23" in encoded
    assert "2" in encoded
    assert "e-" not in encoded


def test_run_hash_composite_stability():
    run_hash = hash_run_hash(
        snapshot_hash="snapshot",
        config_hash="config",
        run_config_hash="run-config",
        committee_packet_hash="committee",
        decision_hash="decision",
    )

    run_hash_repeat = hash_run_hash(
        snapshot_hash="snapshot",
        config_hash="config",
        run_config_hash="run-config",
        committee_packet_hash="committee",
        decision_hash="decision",
    )

    assert run_hash == run_hash_repeat
