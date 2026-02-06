from __future__ import annotations

import argparse
from pathlib import Path

from src.core.config.loader import load_json_file, load_manifest, sha256_digest
from src.core.orchestration import Orchestrator
from src.core.utils.determinism import stable_json_dumps


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IMP-01 orchestration skeleton")
    parser.add_argument("--snapshot", required=True, help="Path to portfolio snapshot JSON")
    parser.add_argument("--portfolio_config", required=True, help="Path to portfolio config JSON")
    parser.add_argument("--run_config", required=True, help="Path to run config JSON")
    parser.add_argument("--config_snapshot", required=True, help="Path to config snapshot JSON")
    parser.add_argument("--manifest", required=False, help="Path to release manifest JSON")
    parser.add_argument("--run_id", required=False, help="Optional run_id override")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    snapshot = load_json_file(Path(args.snapshot))
    portfolio_config = load_json_file(Path(args.portfolio_config))
    run_config = load_json_file(Path(args.run_config))
    config_snapshot = load_json_file(Path(args.config_snapshot))
    manifest = load_manifest(Path(args.manifest)) if args.manifest else None

    config_hashes = {
        "run_config_hash": sha256_digest(run_config.raw_bytes),
        "config_snapshot_hash": sha256_digest(config_snapshot.raw_bytes),
    }

    orchestrator = Orchestrator()
    result = orchestrator.run(
        portfolio_snapshot_data=snapshot.data,
        portfolio_config_data=portfolio_config.data,
        run_config_data=run_config.data,
        config_snapshot_data=config_snapshot.data,
        manifest_data=manifest,
        config_hashes=config_hashes,
        run_id=args.run_id,
    )

    print(stable_json_dumps(result.model_dump()))


if __name__ == "__main__":
    main()
