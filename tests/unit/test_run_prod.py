from __future__ import annotations

import json
from pathlib import Path

from src.cli import run_prod


def test_run_prod_writes_artifacts(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    portfolio_path = repo_root / "fixtures" / "portfolio_snapshot_prod_example.json"
    out_dir = tmp_path / "artifacts"

    run_prod.run_prod(portfolio_path=portfolio_path, out_dir=out_dir)

    summary_path = out_dir / "summary.json"
    runlog_path = out_dir / "runlog.json"
    assert summary_path.exists()
    assert runlog_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("outcome") != "FAILED":
        assert (out_dir / "output_packet.json").exists()


def test_run_prod_writes_failure_report_on_exception(tmp_path: Path) -> None:
    bad_portfolio = tmp_path / "bad_portfolio.json"
    bad_portfolio.write_text("{not valid json", encoding="utf-8")
    out_dir = tmp_path / "out"

    success = run_prod.run_prod(portfolio_path=bad_portfolio, out_dir=out_dir)

    assert not success
    assert (out_dir / "summary.json").exists()
    assert (out_dir / "runlog.json").exists()
    assert (out_dir / "failure_report.md").exists()
