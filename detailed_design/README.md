# Detailed Design (DD) — Traceability Index

This directory contains the **Detailed Design artifacts** for the Agentic Investment System.
Each document maps directly to the High Level Design (HLD) and task plan.

---

## DD Artifact Index

| DD ID | File | Purpose | HLD Trace |
|-----|------|--------|----------|
| DD-01 | DD-01_SCHEMA_SPECIFICATIONS.md | Authoritative schemas, invariants, registries | HLD §5, §7 |
| DD-02 | DD-02_DATA_CONTRACTS.md | Agent-to-agent data contracts | HLD §5 |
| DD-03 | DD-03_AGENT_INTERFACE_CONTRACTS.md | Agent inputs/outputs & authority | HLD §3 |
| DD-04 | DD-04_ORCHESTRATION_FLOW.md | Supporting execution flow | HLD §4 |
| DD-04 | DD-04_ORCHESTRATION_STATE_MACHINE.md | Deterministic orchestration logic | HLD §4 |
| DD-05 | DD-05_PENALTY_ENGINE_SPEC.md | Penalty categories & scoring rules | HLD §7 |
| DD-06 | DD-06_GOVERNANCE_RULES.md | Veto, override, escalation hierarchy | HLD §3, §7 |
| DD-07 | DD-07_CANONICALIZATION_SPEC.md | Deterministic hashing & reproducibility | HLD §6 |
| DD-08 | DD-08_ORCHESTRATION_GUARDS.md | Safety rails & guard enforcement | HLD §4, §7 |
| DD-09 | DD-09_TEST_FIXTURE_SPECIFICATIONS.md | Test vectors & validation cases | HLD §8 |

---

## Design Principles

- Portfolio-first
- Hard-stops beat penalties
- Deterministic execution
- Governance cannot be bypassed
- No invented numbers

---

## Notes

- File numbering reflects **design authority order**, not creation order.
- Supporting documents (e.g. orchestration flow) intentionally share a DD number suffix.
- Content was preserved exactly during renaming.

---

## IMP-01 Skeleton (Foundation)

This repository includes an IMP-01 orchestration skeleton that enforces schema validation, release manifest hash checks, and G0/G1 guard scaffolding. It produces RunLog and FailedRunPacket outputs for FAILED or VETOED outcomes but does not execute agents, penalties, aggregation, or canonical hashing.

### Run the skeleton CLI

```bash
python -m src.cli.run \
  --snapshot fixtures/portfolio_snapshot.json \
  --portfolio_config fixtures/portfolio_config.json \
  --run_config fixtures/run_config.json \
  --config_snapshot fixtures/config_snapshot.json \
  --manifest config/release_manifest.json
```

### Run tests

```bash
pytest
```
