# IMP-02 Acceptance Checklist — Determinism & Canonicalization

This checklist is the single source of truth for IMP-02 acceptance. Every item is mandatory and blocking unless explicitly stated otherwise.

## 1. Scope Guardrails

### Must NOT introduce
- ⬜ Any change to IMP-01 behavior, output schemas, or deterministic run flow beyond canonicalization and hashing; IMP-01 outputs remain valid and unchanged for existing fixtures and tests.
- ⬜ Any runtime timestamps, wall-clock time usage, or time-based ordering inside canonical payloads or hashes.
- ⬜ Any non-deterministic ordering (insertion order, set order, thread order) in canonical payloads or hashes.
- ⬜ Any hashing or serialization of veto logs, runtime logs, or narrative-only fields.
- ⬜ Any change to governance precedence or outcome classification (remains per DD-06/DD-08 and IMP-01 scaffolding).
- ⬜ Any change to fixture formats, baseline fixtures, or release bundle structures.

### Is allowed to introduce
- ⬜ Canonical JSON serialization for decision-significant payloads per DD-07.
- ⬜ Deterministic ordering for holdings, agent outputs, penalties, concentration breaches, and dictionaries per DD-07.
- ⬜ Canonical hashes defined in DD-07 (`snapshot_hash`, `config_hash`, `run_config_hash`, `holding_packet_hash`, `committee_packet_hash`, `decision_hash`, `run_hash`) with emission rules.
- ⬜ Validation errors and explicit canonicalization failure classifications as specified in DD-07.

## 2. Canonicalization Rules

### Canonical JSON serialization requirements
- ⬜ UTF-8 encoding with no whitespace and lexicographically sorted keys for all dictionaries.
- ⬜ Stable numeric formatting: integers without decimals; floats with `.` decimal separator, no trailing zeros, and no exponent notation.
- ⬜ `NaN` and `Infinity` are not present in canonical payloads; they are mapped to `null` only when allowed by DD-07.
- ⬜ Booleans are serialized as `true`/`false`; nulls as `null` only when decision-significant.
- ⬜ Identifier fields (e.g., `holding_id`, `agent_name`) are trimmed; other strings preserve case and punctuation.

### Deterministic ordering rules (mandatory)
- ⬜ Holdings ordered by `holding_id` (lexicographic, case-sensitive).
- ⬜ Agent outputs ordered by `agent_name` (lexicographic).
- ⬜ Penalty items ordered by `category` → `reason` → `source_agent`.
- ⬜ Concentration breaches ordered by `breach_type` → `identifier`.
- ⬜ Dictionaries serialized with lexicographically sorted keys; insertion order is ignored.

### Explicit exclusion of runtime / timestamp fields
- ⬜ `run_id`, `start_time`, `end_time`, `generated_at`, `retrieval_timestamp`, execution durations, and agent timing metadata are excluded from canonical payloads and hashes.
- ⬜ Veto logs and runtime log ordering metadata are excluded from canonical payloads and hashes.
- ⬜ Narrative-only fields (`notes`, `limitations`, `disclaimers`, `recovery_suggestions`) are excluded from canonical payloads and hashes.

## 3. Hashing Requirements

### Required hashes
- ⬜ `snapshot_hash` computed from canonical `PortfolioSnapshot`.
- ⬜ `config_hash` computed from canonical `PortfolioConfig`.
- ⬜ `run_config_hash` computed from canonical `RunConfig`.
- ⬜ `holding_packet_hash` computed for each canonical HoldingPacket.
- ⬜ `committee_packet_hash` computed from canonical PortfolioCommitteePacket.
- ⬜ `decision_hash` computed from canonical final outcome packet.
- ⬜ `run_hash` computed as SHA-256 over the canonical JSON object containing `snapshot_hash`, `config_hash`, `run_config_hash`, `committee_packet_hash`, and `decision_hash`.

### Hash computation rules (canonical-only)
- ⬜ SHA-256 used on canonical JSON string only; output is lowercase hex.
- ⬜ Hash inputs use only canonicalized, deterministically ordered, decision-significant fields per DD-07.

### Hash exclusion rules
- ⬜ Timestamps, diagnostics, runtime metadata, veto logs, and narrative-only fields never affect any hash.
- ⬜ For non-completed outcomes (`VETOED`, `FAILED`, `SHORT_CIRCUITED`), `committee_packet_hash`, `decision_hash`, and `run_hash` are withheld; only `snapshot_hash`, `config_hash`, and `run_config_hash` may be recorded.

## 4. Determinism Invariants

- ⬜ Identical logical inputs produce identical canonical payloads and identical hashes across environments.
- ⬜ Changes exclusively in excluded fields (timestamps, run IDs, narrative-only fields, runtime logs) do not change canonical hashes.
- ⬜ Any decision-significant change (holdings, weights, config values, scores, penalties, outcomes, caps, overrides) produces different hashes.
- ⬜ Canonicalization is locale- and timezone-invariant (UTC base, locale-invariant numeric formatting).

## 5. Test Coverage (Blocking)

### Required test categories
- ⬜ Canonicalization/Hash Determinism Tests per DD-10 (DD-07 coverage is mandatory and blocking).
- ⬜ Deterministic Replay Tests with ordering variance and runtime metadata variance.
- ⬜ Contract Tests and Schema Validation Tests remain passing with no regression in IMP-01 outputs.
- ⬜ Regression & Non-Regression Tests validate no decision-significant drift in baseline fixtures.

### Conditions that fail acceptance
- ⬜ Any mismatch between expected and actual canonical hashes for equivalent inputs.
- ⬜ Any change in baseline fixture outputs or hashes without explicit versioning and governance review.
- ⬜ Any non-deterministic ordering or locale-sensitive serialization detected.

### Prohibition on flaky or time-dependent tests
- ⬜ All tests use fixed, deterministic fixtures (DD-09) and fixed timestamps.
- ⬜ Tests do not depend on wall-clock time, environment locale, or randomness.

## 6. Logging & Auditability

### Required RunLog fields
- ⬜ RunLog records `snapshot_hash`, `config_hash`, and `run_config_hash` for all runs.
- ⬜ RunLog records `committee_packet_hash`, `decision_hash`, and `run_hash` only when `portfolio_run_outcome=COMPLETED`.
- ⬜ RunLog retains governance outcome classification and guard failure indicators without embedding excluded fields into canonical hashes.

### Hash reproducibility requirements
- ⬜ Recomputing hashes from stored canonical payloads reproduces the emitted hashes exactly.
- ⬜ Hash recomputation remains stable across environments with identical inputs and canonicalization rules.

## 7. Deployment Alignment

- ⬜ Phase 1 (Local/Developer Validation): deterministic replay, canonicalization/hash tests, governance enforcement, and portfolio outcome tests are all passing and blocking per DD-10/DD-11.
- ⬜ Phase 2 (Integration Environment): repeated fixture replays produce identical hashes and outcomes with no determinism drift.
- ⬜ No phase proceeds with warnings for determinism or canonicalization failures; any such failure blocks promotion.

## 8. Exit Criteria

- ⬜ All items in Sections 1–7 are satisfied without exception.
- ⬜ No IMP-01 regression is detected in fixtures, outputs, schemas, or run logs.
- ⬜ Canonicalization, hashing, and determinism tests pass in all required phases per DD-10/DD-11.
- ⬜ Failure of any checklist item blocks progression to IMP-03.
