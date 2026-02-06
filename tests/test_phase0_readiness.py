from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.phase0_readiness import run_phase0_readiness


FIXED_NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_json_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def _ensure_utc_env() -> None:
    os.environ["TZ"] = "UTC"
    if hasattr(time, "tzset"):
        time.tzset()


def _make_config_bundle(root: Path) -> dict:
    config_dir = root / "config"
    hard_stop = config_dir / "hard_stop_registry.json"
    penalty = config_dir / "penalty_registry.json"
    agent_registry = config_dir / "agent_registry.json"
    _write_json(hard_stop, {"fields": ["base_currency"]})
    _write_json(penalty, {"fields": ["cash", "runway_months"]})
    _write_json(agent_registry, {"agents": {"DIO": {"version": "0.1", "enabled": True}}})

    run_config_fast = config_dir / "RunConfig_FAST.json"
    run_config_deep = config_dir / "RunConfig_DEEP.json"
    _write_json(run_config_fast, {"run_mode": "FAST"})
    _write_json(run_config_deep, {"run_mode": "DEEP"})

    config_snapshot = {
        "rubric_version": "v1.0",
        "registries": {
            "hard_stop_field_registry": {
                "path": str(hard_stop),
                "hash": _hash_json_bytes(hard_stop),
            },
            "penalty_critical_field_registry": {
                "path": str(penalty),
                "hash": _hash_json_bytes(penalty),
            },
            "agent_registry": {
                "path": str(agent_registry),
                "hash": _hash_json_bytes(agent_registry),
            },
            "scoring_rubric": {
                "dimensions": [
                    {
                        "name": "quality",
                        "metric_key": "quality",
                        "weight": 100.0,
                        "scale_min": 0.0,
                        "scale_max": 100.0,
                        "higher_is_better": True,
                    }
                ]
            },
        },
        "hash": "snapshot-hash",
    }
    config_snapshot_path = config_dir / "config_snapshot.json"
    _write_json(config_snapshot_path, config_snapshot)

    return {
        "config_dir": config_dir,
        "run_config_fast": run_config_fast,
        "run_config_deep": run_config_deep,
        "config_snapshot": config_snapshot_path,
    }


def _make_fixtures(root: Path) -> Path:
    fixtures_dir = root / "fixtures"
    created_at = "2025-01-01T00:00:00Z"

    run_config_fixture = {
        "fixture_id": "RunConfig_FAST",
        "version": "1.0",
        "description": "FAST run config",
        "created_at_utc": created_at,
        "payload": {"run_mode": "FAST"},
    }
    _write_json(fixtures_dir / "config" / "RunConfig_FAST.json", run_config_fixture)

    portfolio_fixture = {
        "fixture_id": "PortfolioSnapshot_N1",
        "version": "1.0",
        "description": "Single holding snapshot",
        "created_at_utc": created_at,
        "payload": {
            "portfolio_id": "PORT-1",
            "as_of_date": "2025-01-01T00:00:00Z",
            "holdings": [
                {
                    "identity": {"holding_id": "HOLDING-1", "ticker": "AAA"},
                    "weight": 1.0,
                    "currency": "USD",
                    "metrics": {
                        "quality": {
                            "value": 80.0,
                            "source_ref": {
                                "origin": "seeded",
                                "as_of_date": "2024-12-31T00:00:00Z",
                                "retrieval_timestamp": "2025-01-01T00:00:00Z",
                            },
                        }
                    },
                }
            ],
            "retrieval_timestamp": "2025-01-01T00:00:00Z",
        },
    }
    _write_json(fixtures_dir / "portfolio" / "PortfolioSnapshot_N1.json", portfolio_fixture)

    seeded_fixture = {
        "fixture_id": "SeededData",
        "version": "1.0",
        "description": "Seeded data",
        "created_at_utc": created_at,
        "payload": {
            "metrics": {
                "cash": {
                    "value": 100.0,
                    "source_ref": {
                        "origin": "seeded",
                        "as_of_date": "2024-12-31T00:00:00Z",
                        "retrieval_timestamp": "2025-01-01T00:00:00Z",
                    },
                }
            }
        },
    }
    _write_json(fixtures_dir / "seeded" / "SeededData.json", seeded_fixture)

    expected_fixture = {
        "fixture_id": "TF-01_expected_portfolio_packet",
        "version": "1.0",
        "description": "Expected output",
        "created_at_utc": created_at,
        "payload": {
            "run_id": "RUN-1",
            "portfolio_id": "PORT-1",
            "portfolio_run_outcome": "COMPLETED",
        },
    }
    _write_json(fixtures_dir / "expected" / "TF-01_expected_portfolio_packet.json", expected_fixture)

    return fixtures_dir


def test_phase0_happy_path(tmp_path: Path) -> None:
    _ensure_utc_env()
    bundle = _make_config_bundle(tmp_path)
    fixtures_dir = _make_fixtures(tmp_path)
    output_dir = tmp_path / "release_manifests"

    result = run_phase0_readiness(
        [
            "--release",
            "r1",
            "--config-dir",
            str(bundle["config_dir"]),
            "--fixtures-dir",
            str(fixtures_dir),
            "--out",
            str(output_dir),
        ],
        now_func=lambda: FIXED_NOW,
    )

    assert not result.errors
    assert result.manifest_path is not None
    assert result.manifest_path.exists()
    assert result.attestation_path.exists()


def test_phase0_missing_registry_fails(tmp_path: Path) -> None:
    _ensure_utc_env()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    run_config = config_dir / "RunConfig_FAST.json"
    _write_json(run_config, {"run_mode": "FAST"})

    config_snapshot = {
        "rubric_version": "v1.0",
        "registries": {
            "hard_stop_field_registry": {"path": str(config_dir / "missing.json"), "hash": "abc"},
            "penalty_critical_field_registry": {"path": str(config_dir / "missing2.json"), "hash": "def"},
        },
        "hash": "snapshot-hash",
    }
    _write_json(config_dir / "config_snapshot.json", config_snapshot)

    fixtures_dir = _make_fixtures(tmp_path)
    output_dir = tmp_path / "release_manifests"

    result = run_phase0_readiness(
        [
            "--release",
            "r1",
            "--config-dir",
            str(config_dir),
            "--fixtures-dir",
            str(fixtures_dir),
            "--out",
            str(output_dir),
        ],
        now_func=lambda: FIXED_NOW,
    )

    assert result.errors


def test_phase0_missing_fixture_metadata_fails(tmp_path: Path) -> None:
    _ensure_utc_env()
    bundle = _make_config_bundle(tmp_path)
    fixtures_dir = tmp_path / "fixtures"
    _write_json(fixtures_dir / "config" / "RunConfig_FAST.json", {"payload": {"run_mode": "FAST"}})
    output_dir = tmp_path / "release_manifests"

    result = run_phase0_readiness(
        [
            "--release",
            "r1",
            "--config-dir",
            str(bundle["config_dir"]),
            "--fixtures-dir",
            str(fixtures_dir),
            "--out",
            str(output_dir),
        ],
        now_func=lambda: FIXED_NOW,
    )

    assert result.errors


def test_phase0_fixture_timestamp_without_z_fails(tmp_path: Path) -> None:
    _ensure_utc_env()
    bundle = _make_config_bundle(tmp_path)
    fixtures_dir = tmp_path / "fixtures"
    bad_fixture = {
        "fixture_id": "RunConfig_FAST",
        "version": "1.0",
        "description": "bad timestamp",
        "created_at_utc": "2025-01-01T00:00:00+00:00",
        "payload": {"run_mode": "FAST"},
    }
    _write_json(fixtures_dir / "config" / "RunConfig_FAST.json", bad_fixture)
    output_dir = tmp_path / "release_manifests"

    result = run_phase0_readiness(
        [
            "--release",
            "r1",
            "--config-dir",
            str(bundle["config_dir"]),
            "--fixtures-dir",
            str(fixtures_dir),
            "--out",
            str(output_dir),
        ],
        now_func=lambda: FIXED_NOW,
    )

    assert result.errors


def test_phase0_seeded_missing_source_ref_fails(tmp_path: Path) -> None:
    _ensure_utc_env()
    bundle = _make_config_bundle(tmp_path)
    fixtures_dir = tmp_path / "fixtures"
    created_at = "2025-01-01T00:00:00Z"

    _write_json(
        fixtures_dir / "seeded" / "SeededData.json",
        {
            "fixture_id": "SeededData",
            "version": "1.0",
            "description": "seeded",
            "created_at_utc": created_at,
            "payload": {"metrics": {"cash": {"value": 123.0}}},
        },
    )
    _write_json(
        fixtures_dir / "config" / "RunConfig_FAST.json",
        {
            "fixture_id": "RunConfig_FAST",
            "version": "1.0",
            "description": "FAST",
            "created_at_utc": created_at,
            "payload": {"run_mode": "FAST"},
        },
    )
    _write_json(
        fixtures_dir / "portfolio" / "PortfolioSnapshot_N1.json",
        {
            "fixture_id": "PortfolioSnapshot_N1",
            "version": "1.0",
            "description": "portfolio",
            "created_at_utc": created_at,
            "payload": {
                "portfolio_id": "PORT-1",
                "as_of_date": "2025-01-01T00:00:00Z",
                "holdings": [],
            },
        },
    )
    _write_json(
        fixtures_dir / "expected" / "TF-01_expected_portfolio_packet.json",
        {
            "fixture_id": "TF-01_expected_portfolio_packet",
            "version": "1.0",
            "description": "expected",
            "created_at_utc": created_at,
            "payload": {
                "run_id": "RUN-1",
                "portfolio_id": "PORT-1",
                "portfolio_run_outcome": "COMPLETED",
            },
        },
    )

    output_dir = tmp_path / "release_manifests"

    result = run_phase0_readiness(
        [
            "--release",
            "r1",
            "--config-dir",
            str(bundle["config_dir"]),
            "--fixtures-dir",
            str(fixtures_dir),
            "--out",
            str(output_dir),
        ],
        now_func=lambda: FIXED_NOW,
    )

    assert result.errors


def test_phase0_hash_determinism(tmp_path: Path) -> None:
    _ensure_utc_env()
    bundle = _make_config_bundle(tmp_path)
    fixtures_dir = _make_fixtures(tmp_path)
    output_dir = tmp_path / "release_manifests"

    first = run_phase0_readiness(
        [
            "--release",
            "r1",
            "--config-dir",
            str(bundle["config_dir"]),
            "--fixtures-dir",
            str(fixtures_dir),
            "--out",
            str(output_dir),
        ],
        now_func=lambda: FIXED_NOW,
    )
    second = run_phase0_readiness(
        [
            "--release",
            "r1",
            "--config-dir",
            str(bundle["config_dir"]),
            "--fixtures-dir",
            str(fixtures_dir),
            "--out",
            str(output_dir),
        ],
        now_func=lambda: FIXED_NOW,
    )

    assert first.manifest_path
    assert second.manifest_path
    manifest_a = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    manifest_b = json.loads(second.manifest_path.read_text(encoding="utf-8"))

    assert manifest_a["hashes"] == manifest_b["hashes"]
