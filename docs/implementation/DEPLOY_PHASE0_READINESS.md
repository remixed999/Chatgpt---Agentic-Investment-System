# Phase 0 Deployment Readiness (DD-11)

## Overview
Phase 0 is the **pre-deployment readiness gate** that blocks promotion unless the release bundle is immutable, schema-valid, and environment-parity safe. The checks align with:

- **DD-11 Phase 0 readiness gates**
- **DD-07 canonicalization rules**
- **DD-08 determinism/emission guards**

## What Phase 0 Enforces

1. **Release manifest hash pinning**
   - `config/release_bundle/release_manifest.json` must exist.
   - Every bundle file is pinned to a SHA-256 hash.
   - Any hash mismatch, missing file, or extra file is a **blocking failure**.

2. **Schema + contract validation**
   - `PortfolioSnapshot`, `PortfolioConfig`, `RunConfig`, and `ConfigSnapshot`
     must validate against the Pydantic models.
   - Any validation error is a **blocking failure**.

3. **Environment parity checks**
   - UTC-only time handling (no local timezone drift).
   - Stable JSON serialization via `stable_json_dumps`.
   - Canonical float formatting without exponent notation (DD-07).
   - No `datetime.now`, `time.time`, or `uuid4` in Phase 0/1 tooling.

4. **Deterministic artifacts**
   - On success, Phase 0 writes
     `artifacts/release/phase0_report.json` with deterministic content.

## How to Run

```bash
python -m src.cli.release_phase0 --bundle ./config/release_bundle
```

## What Blocks Promotion

Phase 0 fails and blocks promotion when:

- The manifest is missing or any hash differs.
- Required bundle files are missing or unpinned.
- Any bundle schema/contract validation fails.
- Parity checks detect non-UTC handling, unstable serialization, or forbidden runtime patterns.

## Artifacts

When Phase 0 passes:

- `artifacts/release/phase0_report.json` is generated.
- The report includes manifest hashes, parity results, schema validation, and bundle identifiers.
