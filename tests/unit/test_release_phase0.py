from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from src.release.manifest import compute_manifest
from src.release.parity import run_parity_checks
from src.release.phase0 import run_phase0


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _ensure_utc_env() -> None:
    os.environ["TZ"] = "UTC"
    if hasattr(time, "tzset"):
        time.tzset()


def _make_bundle(bundle_dir: Path) -> None:
    _write_json(
        bundle_dir / "portfolio_snapshot.json",
        {
            "portfolio_id": "PORT-1",
            "as_of_date": "2025-01-01T00:00:00Z",
            "holdings": [],
            "cash_pct": 0.0,
        },
    )
    _write_json(bundle_dir / "portfolio_config.json", {"base_currency": "USD"})
    _write_json(bundle_dir / "run_config.json", {"run_mode": "FAST"})
    _write_json(
        bundle_dir / "config_snapshot.json",
        {
            "rubric_version": "v1",
            "hard_stop_field_registry": {},
            "penalty_critical_field_registry": {},
        },
    )


def _write_manifest(bundle_dir: Path) -> None:
    manifest = compute_manifest(bundle_dir)
    manifest["release_id"] = "test-release"
    manifest["created_at_utc"] = "2025-01-01T00:00:00Z"
    _write_json(bundle_dir / "release_manifest.json", manifest)


def test_phase0_manifest_drift_blocks(tmp_path: Path) -> None:
    _ensure_utc_env()
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    _make_bundle(bundle_dir)
    _write_manifest(bundle_dir)

    ok_result = run_phase0(bundle_dir)
    assert ok_result.ok

    path = bundle_dir / "portfolio_config.json"
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")

    bad_result = run_phase0(bundle_dir)
    assert not bad_result.ok
    assert any("Hash mismatch" in violation for violation in bad_result.violations)


def test_parity_checks_flag_forbidden_runtime_patterns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _ensure_utc_env()
    sample = tmp_path / "forbidden.py"
    sample.write_text("from datetime import datetime\nvalue = datetime.now()\n", encoding="utf-8")
    monkeypatch.setattr("src.release.parity.PARITY_SCAN_PATHS", [sample])
    violations = run_parity_checks()
    assert any("datetime now usage" in violation for violation in violations)
