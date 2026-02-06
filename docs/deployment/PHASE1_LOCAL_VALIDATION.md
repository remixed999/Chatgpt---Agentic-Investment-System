# Phase 1 — Local / Developer Validation Gates

## Overview
Phase 1 is the local validation harness that runs **after Phase 0 readiness** and blocks promotion if any gate fails. It validates:

- Contracts (schema + agent envelopes + config)
- Determinism / replay canonicalization
- Governance precedence enforcement
- Portfolio outcome behavior

Phase 1 produces artifacts:

- `artifacts/phase1/phase1_report.json`
- `artifacts/phase1/phase1_report.md`
- `artifacts/phase1/replay_logs/*.json`
- `artifacts/phase1/hash_baselines/*.json`
- `artifacts/phase1/test_results/pytest.xml`

## Run Phase 1 Locally

```bash
python -m src.release.phase1 \
  --bundle ./config/release_bundle \
  --fixtures ./fixtures \
  --out_dir ./artifacts/phase1 \
  --runs 3
```

Or use the convenience script:

```bash
./scripts/phase1_local_validation.sh phase1-local
```

## Adding New Fixtures

1. Add fixture files under `fixtures/` with metadata (`fixture_id`, `version`, `description`, `created_at_utc`).
2. Ensure files are placed in one of the required fixture directories:
   - `fixtures/config/`
   - `fixtures/portfolio/`
   - `fixtures/seeded/`
   - `fixtures/expected/`
3. Update `src/release/phase1.py` to include the new fixture in the replay matrix if it is part of the deterministic replay gate.

## Blocking Failures

Phase 1 fails if any of the following occur:

- Phase 0 readiness fails (missing bundle assets, invalid fixtures, schema drift).
- Any Phase 1 pytest suite fails (unit, contract, determinism, governance, canonicalization, outcomes).
- Deterministic replay detects mismatched hashes or outcomes across runs.

## Artifact Locations

All artifacts are written to the `--out_dir` path. By default:

- `artifacts/phase1/phase1_report.json`
- `artifacts/phase1/phase1_report.md`
- `artifacts/phase1/replay_logs/`
- `artifacts/phase1/hash_baselines/`
- `artifacts/phase1/test_results/pytest.xml`
