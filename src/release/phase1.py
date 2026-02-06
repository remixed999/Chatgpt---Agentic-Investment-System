from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.testing.replay import BundlePaths, FixturePaths, replay_n_times
from tools.phase0_readiness import run_phase0_readiness


UTC = timezone.utc


@dataclass
class Phase1Check:
    name: str
    status: str
    details: Dict[str, Any]


@dataclass
class Phase1Failure:
    check: str
    error: str
    fixture_id: Optional[str] = None


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 1 local validation gates")
    parser.add_argument("--bundle", required=True, help="Path to the release bundle config directory")
    parser.add_argument("--fixtures", required=True, help="Path to fixture directory")
    parser.add_argument("--out_dir", required=True, help="Output directory for Phase 1 artifacts")
    parser.add_argument("--runs", type=int, default=1, help="Number of deterministic replay runs")
    return parser.parse_args(argv)


def run_phase1(argv: List[str]) -> int:
    args = _parse_args(argv)
    bundle_dir = Path(args.bundle)
    fixtures_dir = Path(args.fixtures)
    out_dir = Path(args.out_dir)
    runs = max(1, args.runs)

    out_dir.mkdir(parents=True, exist_ok=True)
    replay_dir = out_dir / "replay_logs"
    hash_dir = out_dir / "hash_baselines"
    test_dir = out_dir / "test_results"
    replay_dir.mkdir(parents=True, exist_ok=True)
    hash_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    checks: List[Phase1Check] = []
    failures: List[Phase1Failure] = []
    hashes_report: List[Dict[str, Any]] = []

    release_id = f"phase1_{bundle_dir.name or 'local'}"
    phase0_out_dir = out_dir / "phase0"
    phase0_out_dir.mkdir(parents=True, exist_ok=True)

    phase0_result = run_phase0_readiness(
        [
            "--release",
            release_id,
            "--config-dir",
            str(bundle_dir),
            "--fixtures-dir",
            str(fixtures_dir),
            "--out",
            str(phase0_out_dir),
        ]
    )
    if phase0_result.errors:
        checks.append(
            Phase1Check(
                name="phase0_readiness",
                status="FAIL",
                details={"errors": phase0_result.errors},
            )
        )
        failures.extend(
            Phase1Failure(check="phase0_readiness", error=error) for error in phase0_result.errors
        )
        _write_report(
            out_dir=out_dir,
            status="FAIL",
            runs=runs,
            fixture_ids=[],
            checks=checks,
            hashes=hashes_report,
            failures=failures,
        )
        return 1

    checks.append(
        Phase1Check(
            name="phase0_readiness",
            status="PASS",
            details={"manifest_path": str(phase0_result.manifest_path) if phase0_result.manifest_path else None},
        )
    )

    pytest_cmd = [
        "pytest",
        "tests/unit",
        "tests/contract",
        "tests/determinism",
        "tests/governance",
        "tests/canonicalization",
        "tests/outcomes",
        "--junitxml",
        str(test_dir / "pytest.xml"),
    ]
    pytest_result = subprocess.run(pytest_cmd, capture_output=True, text=True)
    pytest_status = "PASS" if pytest_result.returncode == 0 else "FAIL"
    checks.append(
        Phase1Check(
            name="pytest_phase1_suites",
            status=pytest_status,
            details={
                "command": " ".join(pytest_cmd),
                "stdout": pytest_result.stdout,
                "stderr": pytest_result.stderr,
            },
        )
    )
    if pytest_result.returncode != 0:
        failures.append(
            Phase1Failure(check="pytest_phase1_suites", error="pytest suites failed")
        )

    fixture_map = _fixture_matrix(fixtures_dir)
    bundle_paths = BundlePaths()
    deterministic_pass = True

    for fixture_id, fixture_paths in fixture_map.items():
        replay_results = replay_n_times(
            fixture_id,
            runs,
            fixture_paths=fixture_paths,
            bundle_paths=bundle_paths,
        )
        baseline = replay_results[0]
        mismatch = _detect_mismatch(baseline, replay_results[1:])
        if mismatch:
            deterministic_pass = False
            diff_path = replay_dir / f"{fixture_id}_diff.json"
            diff_path.write_text(json.dumps(mismatch, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            failures.append(
                Phase1Failure(
                    check="deterministic_replay",
                    fixture_id=fixture_id,
                    error="determinism mismatch",
                )
            )

        replay_payload = [
            {
                "hashes": result.hashes,
                "outcomes": result.outcomes,
                "logs": result.logs,
            }
            for result in replay_results
        ]
        replay_path = replay_dir / f"{fixture_id}.json"
        replay_path.write_text(json.dumps(replay_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        hash_baseline_path = hash_dir / f"{fixture_id}.json"
        hash_baseline_path.write_text(
            json.dumps({"fixture_id": fixture_id, "baseline": baseline.hashes}, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

        for index, result in enumerate(replay_results):
            hashes_report.append(
                {
                    "fixture_id": fixture_id,
                    "run_index": index,
                    "snapshot_hash": result.hashes.get("snapshot_hash"),
                    "config_hash": result.hashes.get("config_hash"),
                    "run_config_hash": result.hashes.get("run_config_hash"),
                    "decision_hash": result.hashes.get("decision_hash"),
                    "run_hash": result.hashes.get("run_hash"),
                }
            )

    checks.append(
        Phase1Check(
            name="deterministic_replay",
            status="PASS" if deterministic_pass else "FAIL",
            details={"fixtures": sorted(fixture_map.keys()), "runs": runs},
        )
    )

    status = "PASS" if deterministic_pass and pytest_result.returncode == 0 else "FAIL"

    _write_report(
        out_dir=out_dir,
        status=status,
        runs=runs,
        fixture_ids=sorted(fixture_map.keys()),
        checks=checks,
        hashes=hashes_report,
        failures=failures,
    )

    return 0 if status == "PASS" else 1


def _fixture_matrix(fixtures_dir: Path) -> Dict[str, FixturePaths]:
    portfolio_config_path = fixtures_dir / "portfolio_config.json"
    return {
        "TF-01": FixturePaths(
            portfolio_snapshot=fixtures_dir / "portfolio" / "PortfolioSnapshot_N3.json",
            portfolio_config=portfolio_config_path,
            seeded=fixtures_dir / "seeded" / "SeededData_HappyPath.json",
            run_config=fixtures_dir / "config" / "RunConfig_DEEP.json",
            config_snapshot=fixtures_dir / "config" / "ConfigSnapshot_v1.json",
        ),
        "TF-03": FixturePaths(
            portfolio_snapshot=fixtures_dir / "portfolio" / "PortfolioSnapshot_N3.json",
            portfolio_config=portfolio_config_path,
            seeded=fixtures_dir / "seeded" / "SeededData_GRRA_DoNotTrade.json",
            run_config=fixtures_dir / "config" / "RunConfig_DEEP.json",
            config_snapshot=fixtures_dir / "config" / "ConfigSnapshot_v1.json",
        ),
        "TF-14": FixturePaths(
            portfolio_snapshot=fixtures_dir / "portfolio" / "PortfolioSnapshot_TF14_partial_failure.json",
            portfolio_config=portfolio_config_path,
            seeded=fixtures_dir / "seeded" / "SeededData_HappyPath.json",
            run_config=fixtures_dir / "config" / "RunConfig_TF14.json",
            config_snapshot=fixtures_dir / "config" / "ConfigSnapshot_v1.json",
        ),
    }


def _detect_mismatch(baseline, candidates):
    for result in candidates:
        mismatches = []
        if baseline.hashes.get("decision_hash") != result.hashes.get("decision_hash"):
            mismatches.append("decision_hash")
        if baseline.hashes.get("run_hash") != result.hashes.get("run_hash"):
            mismatches.append("run_hash")
        if baseline.hashes.get("holding_packet_hashes") != result.hashes.get("holding_packet_hashes"):
            mismatches.append("holding_packet_hashes")
        if baseline.outcomes != result.outcomes:
            mismatches.append("outcomes")
        if mismatches:
            return {
                "baseline": {
                    "hashes": baseline.hashes,
                    "outcomes": baseline.outcomes,
                },
                "candidate": {
                    "hashes": result.hashes,
                    "outcomes": result.outcomes,
                },
                "differences": sorted(set(mismatches)),
            }
    return None


def _write_report(
    *,
    out_dir: Path,
    status: str,
    runs: int,
    fixture_ids: List[str],
    checks: List[Phase1Check],
    hashes: List[Dict[str, Any]],
    failures: List[Phase1Failure],
) -> None:
    report = {
        "phase": "1",
        "status": status,
        "run_count": runs,
        "fixture_set_used": fixture_ids,
        "checks": [check.__dict__ for check in checks],
        "hashes": hashes,
        "failures": [failure.__dict__ for failure in failures],
    }
    report_path = out_dir / "phase1_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Phase 1 Local Validation Report",
        "",
        f"Status: **{status}**",
        f"Generated at (UTC): {datetime.now(UTC).isoformat().replace('+00:00', 'Z')}",
        "",
        "## Checks",
    ]
    for check in checks:
        lines.append(f"- **{check.name}**: {check.status}")
    if failures:
        lines.append("\n## Failures")
        for failure in failures:
            fixture_note = f" ({failure.fixture_id})" if failure.fixture_id else ""
            lines.append(f"- {failure.check}{fixture_note}: {failure.error}")
    report_md_path = out_dir / "phase1_report.md"
    report_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    sys.exit(run_phase1(sys.argv[1:]))


if __name__ == "__main__":
    main()
