#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <release_id>" >&2
  exit 2
fi

release_id="$1"

python -m tools.phase0_readiness \
  --release "${release_id}" \
  --config-dir config/ \
  --fixtures-dir fixtures/ \
  --out release_manifests/
