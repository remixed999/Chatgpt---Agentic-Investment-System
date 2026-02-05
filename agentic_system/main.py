from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentic_system.config.loader import preflight


# DD-11: intake + preflight only

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agentic System preflight")
    parser.add_argument("--run-config", required=True, help="Path to RunConfig JSON")
    parser.add_argument("--config-snapshot", required=True, help="Path to ConfigSnapshot JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        preflight(Path(args.run_config), Path(args.config_snapshot))
    except (FileNotFoundError, ValueError) as exc:
        print(f"Preflight failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
