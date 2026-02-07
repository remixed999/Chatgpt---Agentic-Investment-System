# ChatGPT — Agentic Investment System

This repository contains a design-first, portfolio-level agentic investment system. The High-Level Design (HLD) is frozen, and Detailed Design (DD) is in progress. No execution or runtime code exists yet.

## Structure

- `hld/`: High-Level Design artifacts (frozen)
- `detailed_design/`: Detailed Design specifications (in progress)
- `directives/`: SOP-style directives, including environment setup
- `delivery/`: Project management and delivery artifacts
- `notes/`: Design decision logs

## Determinism & Canonicalization (IMP-02)

Canonicalization and hashing are applied to decision-significant payloads prior to hash emission. The canonicalizer enforces:

- UTF-8 JSON encoding with sorted keys and no whitespace.
- Deterministic ordering for collections:
  - Holdings sorted by `holding_id`.
  - Agent outputs sorted by `agent_name`.
  - Penalty items sorted by `category`, then `reason`, then `source_agent`.
  - Veto logs sorted by `sequence_number`, `agent_name`, `rule_id`; if any veto log lacks `sequence_number`, veto logs are excluded from canonical hashes.
- Stable numeric formatting (ints without decimals, floats without exponent notation or trailing zeros).

Excluded fields from canonical hashes:

- `run_id`
- Runtime timestamps such as `generated_at` and `retrieval_timestamp`
- Narrative text fields such as `notes`, `disclaimers`, and `limitations`

Hashes are emitted only when the portfolio run outcome is `COMPLETED`. Failed, vetoed, or short-circuited runs omit hash fields entirely.

### Replay validation tests

To run hash stability/replay validation tests:

```bash
pytest
```

## How to run a production-style evaluation

Step 1: Ensure you are at the repo root.

Step 2: Run the production wrapper with a portfolio snapshot:

```bash
python -m src.cli.run_prod --portfolio fixtures/portfolio_snapshot_prod_example.json --out artifacts/prod_run_001
```

Optional flags:

- `--run_mode DEEP|FAST` to override the configured run mode.
- `--prod` to add an execution profile marker to `summary.json`.

Step 3: Inspect the artifacts directory. The wrapper always writes:

- `summary.json`: run_id, portfolio_id, outcome, counts by holding outcome, and any errors.
- `runlog.json`: full run log emitted by the orchestrator.
- `output_packet.json`: the portfolio packet (when the run reaches packet emission).
- `failure_report.md`: present only if the run fails, with step-by-step diagnostics.
