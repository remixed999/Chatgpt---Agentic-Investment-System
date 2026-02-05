from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.core.config.loader import sha256_digest
from src.core.models import RunOutcome
from src.core.orchestration import Orchestrator


FIXED_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _load_fixture(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hash_fixture(path: str) -> str:
    return sha256_digest(Path(path).read_bytes())


def _base_inputs():
    return {
        "portfolio_snapshot_data": _load_fixture("fixtures/portfolio_snapshot.json"),
        "portfolio_config_data": _load_fixture("fixtures/portfolio_config.json"),
        "run_config_data": _load_fixture("fixtures/run_config.json"),
        "config_snapshot_data": _load_fixture("fixtures/config_snapshot.json"),
        "manifest_data": _load_fixture("config/release_manifest.json"),
        "config_hashes": {
            "run_config_hash": _hash_fixture("fixtures/run_config.json"),
            "config_snapshot_hash": _hash_fixture("fixtures/config_snapshot.json"),
        },
    }


def test_missing_base_currency_vetoes_run():
    inputs = _base_inputs()
    inputs["portfolio_config_data"] = {"base_currency": None}
    orchestrator = Orchestrator(now_func=lambda: FIXED_TIME)

    result = orchestrator.run(**inputs)

    assert result.outcome == RunOutcome.VETOED
    assert result.run_log.outcome == RunOutcome.VETOED
    assert result.run_log.started_at_utc == FIXED_TIME
    assert result.run_log.ended_at_utc == FIXED_TIME
    assert "missing_base_currency" in result.run_log.reasons


def test_invalid_schema_fails_run():
    inputs = _base_inputs()
    inputs["portfolio_snapshot_data"] = {
        "as_of_date": "2024-01-01T00:00:00+00:00",
        "holdings": [],
    }
    orchestrator = Orchestrator(now_func=lambda: FIXED_TIME)

    result = orchestrator.run(**inputs)

    assert result.outcome == RunOutcome.FAILED
    assert any("portfolio_id" in reason for reason in result.run_log.reasons)


def test_config_hash_mismatch_fails_run():
    inputs = _base_inputs()
    inputs["manifest_data"] = {
        "run_config_hash": "mismatch",
        "config_snapshot_hash": inputs["config_hashes"]["config_snapshot_hash"],
    }
    orchestrator = Orchestrator(now_func=lambda: FIXED_TIME)

    result = orchestrator.run(**inputs)

    assert result.outcome == RunOutcome.FAILED
    assert "run_config_hash_mismatch" in result.run_log.reasons
