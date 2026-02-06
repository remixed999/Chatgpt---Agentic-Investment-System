# IMP-01 Foundation Skeleton

## Overview
This implementation delivers the minimal IMP-01 orchestration skeleton aligned to DD-11 ordering.
It focuses on deterministic intake validation, fixture-driven runs, and minimal packets/run logs.

## Implemented
- Core Pydantic schemas for intake, outcomes, packets, and run logs in `src/schemas/`.
- Config bundle loader for `config/release_bundle/` inputs.
- Schema/contract gate with deterministic validation outcomes.
- Orchestrator skeleton with:
  - deterministic `run_id`
  - intake validation hard gate
  - identity failure handling
  - partial failure veto threshold logic
  - deterministic run logs
- CLI `python -m src.cli.run_local --bundle ... --out ...`
- IMP-01 fixtures and tests for TF-01/TF-02/TF-04.

## Stubbed / Deferred
- Canonicalization hashing
- Governance precedence
- Penalty engine
- Agents and aggregation logic

## Local Run
```bash
python -m src.cli.run_local --bundle ./config/release_bundle --out ./artifacts/runs/run1
```

## Notes
- Runtime timestamps are forbidden; Phase 1 derives its time base deterministically from fixture inputs (PortfolioSnapshot `as_of_date` preferred).
- Validation errors are classified into portfolio vetoes or holding failures per DD-08.
- Fixtures remain DD-02-shaped (PortfolioSnapshot includes `cash_pct`, holdings include `identity` and `metrics`), even when metrics/agents are stubbed in IMP-01.
