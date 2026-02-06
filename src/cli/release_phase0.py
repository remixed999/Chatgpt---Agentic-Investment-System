from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.core.utils.determinism import stable_json_dumps
from src.release.phase0 import run_phase0, write_report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 0 deployment readiness gate")
    parser.add_argument("--bundle", required=True, help="Path to release bundle directory")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    bundle_dir = Path(args.bundle)
    result = run_phase0(bundle_dir)
    print(stable_json_dumps(result.report))
    if result.ok:
        report_path = Path("artifacts/release/phase0_report.json")
        write_report(report_path, result.report)
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
