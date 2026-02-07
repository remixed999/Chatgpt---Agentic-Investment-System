from __future__ import annotations

import argparse
import traceback
from collections import Counter
from pathlib import Path
from typing import Optional

from src.core.config.loader import load_json
from src.core.models import RunLog, RunOutcome
from src.core.orchestration import Orchestrator
from src.core.orchestration.orchestrator import DEFAULT_RUN_ID, DEFAULT_TIME
from src.core.utils.determinism import stable_json_dumps


RELEASE_BUNDLE_DIR = Path("config") / "release_bundle"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a production-style evaluation wrapper.")
    parser.add_argument("--portfolio", required=True, help="Path to portfolio snapshot JSON")
    parser.add_argument("--out", required=True, help="Output directory for run artifacts")
    parser.add_argument(
        "--run_mode",
        required=False,
        choices=["DEEP", "FAST"],
        help="Override the run mode (DEEP or FAST).",
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Include execution_profile marker in summary output.",
    )
    return parser.parse_args()


def _load_release_bundle(
    bundle_dir: Path,
    run_mode: Optional[str],
) -> tuple[dict, dict, dict]:
    portfolio_config_data = load_json(bundle_dir / "portfolio_config.json")
    run_config_data = load_json(bundle_dir / "run_config.json")
    if run_mode:
        run_config_data = {**run_config_data, "run_mode": run_mode}
    config_snapshot_data = load_json(bundle_dir / "config_snapshot.json")
    return portfolio_config_data, run_config_data, config_snapshot_data


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(stable_json_dumps(payload), encoding="utf-8")


def _build_counts_by_outcome(holding_packets: list) -> dict:
    counter: Counter[str] = Counter()
    for packet in holding_packets:
        outcome = packet.holding_run_outcome
        outcome_value = outcome.value if hasattr(outcome, "value") else str(outcome)
        counter[outcome_value] += 1
    return dict(counter)


def _build_summary(
    *,
    run_id: str,
    portfolio_id: Optional[str],
    outcome: str,
    counts_by_outcome: dict,
    errors: list,
    prod: bool,
) -> dict:
    summary = {
        "run_id": run_id,
        "portfolio_id": portfolio_id,
        "outcome": outcome,
        "counts_by_outcome": counts_by_outcome,
        "errors": errors,
    }
    if prod:
        summary["execution_profile"] = "PROD"
    return summary


def _fallback_runlog(run_id: str, errors: list) -> RunLog:
    return RunLog(
        run_id=run_id,
        started_at_utc=DEFAULT_TIME,
        ended_at_utc=DEFAULT_TIME,
        status="failed",
        outcome=RunOutcome.FAILED,
        reasons=errors,
        config_hashes={},
    )


def _write_failure_report(
    path: Path,
    *,
    failed_step: str,
    exception_text: str,
    stack_trace: str,
    suggested_fix: str,
) -> None:
    content = "\n".join(
        [
            "# Production Run Failure Report",
            "",
            f"**Failing step:** {failed_step}",
            "",
            f"**Exception:** {exception_text}",
            "",
            "**Stack trace:**",
            "```",
            stack_trace,
            "```",
            "",
            f"**Suggested fix:** {suggested_fix}",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def _suggested_fix(failed_step: str) -> str:
    suggestions = {
        "load_portfolio": "Verify the portfolio JSON matches the PortfolioSnapshot schema.",
        "load_release_bundle": "Ensure config/release_bundle contains valid config JSON files.",
        "orchestrator_run": "Check runlog reasons and validate portfolio/config data.",
        "write_artifacts": "Confirm the output directory is writable.",
    }
    return suggestions.get(failed_step, "Review the stack trace and inputs for details.")


def run_prod(
    *,
    portfolio_path: Path,
    out_dir: Path,
    run_mode: Optional[str] = None,
    prod: bool = False,
    bundle_dir: Optional[Path] = None,
) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir = bundle_dir or RELEASE_BUNDLE_DIR

    failed_step = "init"
    exception: Optional[BaseException] = None
    stack_trace = ""
    result = None
    portfolio_snapshot_data: dict = {}
    errors: list = []
    run_id = DEFAULT_RUN_ID

    try:
        failed_step = "load_portfolio"
        portfolio_snapshot_data = load_json(portfolio_path)
        failed_step = "load_release_bundle"
        portfolio_config_data, run_config_data, config_snapshot_data = _load_release_bundle(
            bundle_dir,
            run_mode,
        )
        failed_step = "orchestrator_run"
        orchestrator = Orchestrator(now_func=lambda: DEFAULT_TIME)
        result = orchestrator.run(
            portfolio_snapshot_data=portfolio_snapshot_data,
            portfolio_config_data=portfolio_config_data,
            run_config_data=run_config_data,
            config_snapshot_data=config_snapshot_data,
        )
        run_id = result.run_log.run_id
    except Exception as exc:  # noqa: BLE001 - capture for failure report
        exception = exc
        stack_trace = traceback.format_exc()
        errors = [str(exc)]

    portfolio_id = None
    if isinstance(portfolio_snapshot_data, dict):
        portfolio_id = portfolio_snapshot_data.get("portfolio_id")
    if result and result.packet and not portfolio_id:
        portfolio_id = getattr(result.packet, "portfolio_id", None)

    if result:
        runlog_payload = result.run_log.model_dump(mode="json")
        errors = result.run_log.reasons if result.outcome == RunOutcome.FAILED else []
        counts_by_outcome = _build_counts_by_outcome(result.holding_packets)
        outcome = result.outcome.value
    else:
        runlog_payload = _fallback_runlog(run_id, errors).model_dump(mode="json")
        counts_by_outcome = {}
        outcome = RunOutcome.FAILED.value

    try:
        _write_json(out_dir / "runlog.json", runlog_payload)
        summary_payload = _build_summary(
            run_id=run_id,
            portfolio_id=portfolio_id,
            outcome=outcome,
            counts_by_outcome=counts_by_outcome,
            errors=errors,
            prod=prod,
        )
        _write_json(out_dir / "summary.json", summary_payload)

        if result and result.packet:
            _write_json(out_dir / "output_packet.json", result.packet.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001 - ensure failure report even on write errors
        failed_step = "write_artifacts"
        exception = exc
        stack_trace = traceback.format_exc()

    if exception or (result and result.outcome == RunOutcome.FAILED):
        failure_path = out_dir / "failure_report.md"
        _write_failure_report(
            failure_path,
            failed_step=failed_step,
            exception_text=repr(exception) if exception else "None",
            stack_trace=stack_trace or "N/A (no exception captured)",
            suggested_fix=_suggested_fix(failed_step),
        )

    return exception is None and bool(result) and result.outcome != RunOutcome.FAILED


def main() -> None:
    args = _parse_args()
    run_prod(
        portfolio_path=Path(args.portfolio),
        out_dir=Path(args.out),
        run_mode=args.run_mode,
        prod=args.prod,
    )


if __name__ == "__main__":
    main()
