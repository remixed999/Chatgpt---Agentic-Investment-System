# IMP-04 — Penalty Engine (DD-05)

## Overview
The Penalty Engine computes deterministic, per-holding penalty breakdowns after governance and guard enforcement. It converts DIO signals, agent confidence, FX exposure reports, and data validity flags into standardized penalty items, applies per-category and total caps, and returns an ordered list of penalties for scoring. Penalties are only computed for holdings with `holding_run_outcome=COMPLETED`, and are never evaluated for portfolio or holding outcomes that are VETOED/FAILED/SHORT_CIRCUITED. This maintains DD-06/DD-08 precedence and prevents penalties from overriding vetoes.

## Computation Flow (DD-05)
1. **Hard-stop gate**: If DIO reports integrity veto, missing hard-stop fields, or hard-stop staleness, return an all-zero `PenaltyBreakdown` with empty details.
2. **Build candidate items** from:
   - Category A (missing penalty-critical fields)
   - Category B (staleness within penalty window)
   - Category C (contradictions / integrity)
   - Category D (low-confidence + Devil’s Advocate fatal risk)
   - Category E (FX exposure risk)
   - Category F (corporate actions / data validity)
3. **Deduplicate** items by `(category, reason, source_agent)`.
4. **Apply category caps**, then **apply total cap** (mode dependent).
5. **Sort penalty items** by `category → reason → source_agent` to satisfy DD-07 canonical ordering.
6. **Return** the `PenaltyBreakdown` and record cap enforcement in the holding scorecard notes.

## Deterministic Ordering
Penalty items are sorted lexicographically by:
1. `category` (A → F)
2. `reason`
3. `source_agent`

Cap enforcement uses deterministic drop ordering from DD-05:
- **Per-category caps:** drop smallest magnitude first; for ties, drop lexicographically later `reason`.
- **Total cap:** drop smallest magnitude first; for ties, drop later categories (F → A), then lexicographically later `reason`.

## Cap Enforcement Logging
When category or total caps remove any penalty items, a deterministic note (`penalty_cap_applied`) is appended to the holding `Scorecard.notes`. This is emitted on holding packets but excluded from canonicalization hashes per DD-07.

## Precedence Rules (DD-06/DD-08)
Penalty computation is skipped when:
- portfolio outcome is **VETOED**, **FAILED**, or **SHORT_CIRCUITED**
- holding outcome is **VETOED**, **FAILED**, or **SHORT_CIRCUITED**

This preserves the precedence stack and ensures penalties never override governance vetoes.

## Test Coverage Mapping (DD-09)
Fixture-based tests and orchestration tests map to DD-09 requirements:
- **TF-06**: Non-burn-rate missing cash/runway → Category A penalty (`tests/test_penalty_engine_fixtures.py`).
- **TF-07**: Not applicable cash/runway → no penalty (`tests/test_penalty_engine_fixtures.py`).
- **TF-08**: Staleness threshold hit → Category B penalty (`tests/test_penalty_engine_fixtures.py`).
- **TF-10**: Corporate action split within 90 days → Category F penalty (`tests/test_penalty_engine_fixtures.py`).
- **TF-12**: Total penalty cap enforcement → capped at -35 with deterministic drop order (`tests/test_penalty_engine_fixtures.py`, `tests/test_aggregation.py`).
- **Precedence**: Vetoed holding emits zero penalties (`tests/governance/test_precedence_order.py`).
