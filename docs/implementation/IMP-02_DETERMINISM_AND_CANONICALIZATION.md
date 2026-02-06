# IMP-02 — Determinism & Canonicalization

## Overview
IMP-02 implements deterministic canonicalization and hashing on top of IMP-01 outputs. Canonicalization enforces stable ordering, stable serialization, and explicit exclusion of non-decision metadata so that identical logical inputs produce identical hashes across runs and environments.

This implementation follows DD-07 Canonicalization Specification and the DD-11 Phased Deployment Plan.

## Canonicalized Data
Canonicalization is applied to the decision-significant payloads:

- `PortfolioSnapshot`
- `PortfolioConfig`
- `RunConfig`
- Holding packets
- `PortfolioCommitteePacket`
- Decision payload (committee packet + holding packets)

Deterministic ordering rules include:

- Holdings sorted by `holding_id`
- Agent outputs sorted by `agent_name`
- Penalty items sorted by `category` → `reason` → `source_agent`
- Guard/governance events sorted by `guard_id`
- Concentration breaches sorted by `breach_type` → `identifier`
- All dictionaries serialized with lexicographic key ordering

Identifier fields (`holding_id`, `agent_name`) are trimmed for canonical consistency.

## Explicitly Excluded Fields
The following non-decision metadata is excluded from canonical payloads and hashes:

- `run_id`
- `runlog_ref`
- `start_time`
- `end_time`
- `generated_at`
- `retrieval_timestamp`
- `veto_logs`
- narrative-only fields (`notes`, `limitations`, `disclaimers`, `recovery_suggestions`)

These exclusions prevent runtime metadata or narrative text from affecting deterministic hashes.

## Hash Computation Rules
All hashes are SHA-256 of canonical JSON (UTF-8, no whitespace, sorted keys). Hash inputs:

- `snapshot_hash`: canonical `PortfolioSnapshot`
- `config_hash`: canonical `PortfolioConfig`
- `run_config_hash`: canonical `RunConfig`
- `committee_packet_hash`: canonical `PortfolioCommitteePacket`
- `decision_hash`: canonical decision payload (committee packet + holding packets)
- `run_hash`: canonical JSON object containing `snapshot_hash`, `config_hash`, `run_config_hash`, `committee_packet_hash`, and `decision_hash`

### Hash Gating
Hashes are emitted **only** when `portfolio_run_outcome == COMPLETED`. For `VETOED`, `FAILED`, or `SHORT_CIRCUITED` runs, hashes are withheld to preserve DD-07 emission rules.

## Determinism Guard (G7)
The determinism guard enforces:

- Non-canonical ordering detection for holdings and agent outputs.
- Canonicalization idempotency checks to catch hash instability.

Violations produce `determinism_order_violation` or `determinism_hash_instability` and block progression.

## DD-07 / DD-11 Compliance
This implementation satisfies DD-07 by:

- Enforcing deterministic ordering rules and canonical serialization.
- Excluding non-decision metadata from hashes.
- Emitting hashes only for completed outcomes.

It aligns with DD-11 by ensuring deterministic replay and stable hash baselines across runs and environments.
