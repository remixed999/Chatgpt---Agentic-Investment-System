from __future__ import annotations

from pathlib import Path

from src.release import phase1


def test_phase1_report_is_byte_stable(tmp_path: Path) -> None:
    fixtures_dir = Path(__file__).resolve().parents[2] / "fixtures"
    fixture_map = phase1._fixture_matrix(fixtures_dir)
    report_timestamp = phase1._deterministic_timestamp(fixture_map)

    checks = [
        phase1.Phase1Check(
            name="deterministic_replay",
            status="PASS",
            details={"fixtures": sorted(fixture_map.keys()), "runs": 2},
        )
    ]
    hashes = [
        {
            "fixture_id": "TF-01",
            "run_index": 0,
            "snapshot_hash": "hash-001",
            "config_hash": "hash-002",
            "run_config_hash": "hash-003",
            "decision_hash": "hash-004",
            "run_hash": "hash-005",
        }
    ]
    failures: list[phase1.Phase1Failure] = []

    out_dir_one = tmp_path / "run1"
    out_dir_two = tmp_path / "run2"
    out_dir_one.mkdir()
    out_dir_two.mkdir()

    phase1._write_report(
        out_dir=out_dir_one,
        status="PASS",
        runs=2,
        fixture_ids=sorted(fixture_map.keys()),
        checks=checks,
        hashes=hashes,
        failures=failures,
        report_timestamp=report_timestamp,
    )
    phase1._write_report(
        out_dir=out_dir_two,
        status="PASS",
        runs=2,
        fixture_ids=sorted(fixture_map.keys()),
        checks=checks,
        hashes=hashes,
        failures=failures,
        report_timestamp=report_timestamp,
    )

    assert report_timestamp == "2025-01-01T00:00:00Z"
    assert (out_dir_one / "phase1_report.json").read_bytes() == (
        out_dir_two / "phase1_report.json"
    ).read_bytes()
    assert (out_dir_one / "phase1_report.md").read_bytes() == (
        out_dir_two / "phase1_report.md"
    ).read_bytes()
