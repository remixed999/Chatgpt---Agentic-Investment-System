#!/usr/bin/env bash
set -euo pipefail

release_id=${1:-phase1-local}
bundle_dir=${2:-config/release_bundle}
fixtures_dir=${3:-fixtures}
out_dir=${4:-artifacts/phase1}
runs=${5:-3}

python -m tools.phase0_readiness \
  --release "${release_id}" \
  --config-dir "${bundle_dir}" \
  --fixtures-dir "${fixtures_dir}" \
  --out "${out_dir}/phase0"

python -m src.release.phase1 \
  --bundle "${bundle_dir}" \
  --fixtures "${fixtures_dir}" \
  --out_dir "${out_dir}" \
  --runs "${runs}"

echo "Phase 1 artifacts written to ${out_dir}"
