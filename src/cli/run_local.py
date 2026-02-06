from __future__ import annotations

import argparse
from pathlib import Path

from src.core.config.loader import load_bundle
from src.core.orchestration import Orchestrator
from src.core.utils.determinism import stable_json_dumps


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IMP-01 orchestration skeleton locally.")
    parser.add_argument("--bundle", required=True, help="Path to release bundle directory.")
    parser.add_argument("--out", required=True, help="Output directory for run artifacts.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    bundle_dir = Path(args.bundle)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    bundle = load_bundle(bundle_dir)

    orchestrator = Orchestrator()
    result = orchestrator.run(
        portfolio_snapshot_data=bundle.portfolio_snapshot.model_dump(),
        portfolio_config_data=bundle.portfolio_config.model_dump(),
        run_config_data=bundle.run_config.model_dump(),
        config_snapshot_data=bundle.config_snapshot.model_dump(),
    )

    (out_dir / "runlog.json").write_text(
        stable_json_dumps(result.run_log.model_dump(mode="json")), encoding="utf-8"
    )
    (out_dir / "output_packet.json").write_text(
        stable_json_dumps(result.packet.model_dump(mode="json")), encoding="utf-8"
    )

    summary_path = out_dir / "summary.json"
    summary_path.write_text(
        stable_json_dumps(
            {
                "run_id": result.run_log.run_id,
                "portfolio_outcome": result.packet.portfolio_run_outcome.value,
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
