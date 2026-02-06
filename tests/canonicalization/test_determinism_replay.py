from __future__ import annotations

import json
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


def test_deterministic_replay_canonical_json_and_hashes() -> None:
    inputs = _base_inputs()

    result_a = Orchestrator().run(**inputs)
    result_b = Orchestrator().run(**inputs)

    assert result_a.outcome == RunOutcome.COMPLETED
    assert result_b.outcome == RunOutcome.COMPLETED

    packet_a = result_a.portfolio_committee_packet
    packet_b = result_b.portfolio_committee_packet
    assert packet_a is not None
    assert packet_b is not None

    assert canonical_json_dumps(packet_a.model_dump()) == canonical_json_dumps(packet_b.model_dump())
    assert packet_a.decision_hash == packet_b.decision_hash
    assert packet_a.run_hash == packet_b.run_hash
