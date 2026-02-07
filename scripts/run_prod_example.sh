#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="./artifacts/prod_run_001"
PORTFOLIO_PATH="fixtures/portfolio_snapshot_prod_example.json"

mkdir -p "${ARTIFACT_DIR}"

python -m src.cli.run_prod --portfolio "${PORTFOLIO_PATH}" --out "${ARTIFACT_DIR}"

echo "Production run artifacts written to: ${ARTIFACT_DIR}"
