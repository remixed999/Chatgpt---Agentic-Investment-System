# IMP-03 — Governance & Guards Implementation

## Guard Layer (DD-08)

### Guard ordering (deterministic)
Guards are executed in deterministic order via the registry:

1. **G0** Input/schema + manifest hash validation
2. **G1** Identity & portfolio context
3. **G2** Provenance enforcement (unsourced numeric metrics)
4. **G3** Freshness (no-op placeholder)
5. **G4** Registry completeness
6. **G5** AgentResult envelope conformance
7. **G6** Governance precedence enforcement (GRRA short-circuit)
8. **G7** Deterministic ordering/canonicalization checks
9. **G8** Outcome classification consistency
10. **G9** Partial failure threshold enforcement
11. **G10** Emission eligibility enforcement

### Guard outcomes & enforcement
- Portfolio-level failures/vetoes short-circuit the run immediately and prevent downstream stages.
- Holding-level violations are captured as `GuardViolation` records and drive holding outcomes.
- G9 executes **after holding evaluation and before aggregation**, enforcing strict `>` semantics.
- G10 validates emission eligibility against the terminal outcome and blocks hash emission unless COMPLETED.

## Governance Precedence Stack (DD-06)

Precedence is enforced in the following order:

1. **DIO VETO** (guard outcomes + DIO agent integrity veto)
2. **GRRA SHORT_CIRCUIT** (`do_not_trade_flag`)
3. **Risk Officer VETO** (holding-level veto flags)
4. **LEFO caps**
5. **PSCC caps**
6. **Penalties** (only if not vetoed/short-circuited)
7. **Chair aggregation**

Vetoes/short-circuits prevent any downstream caps/penalties or aggregation from changing outcomes.

## Outcome Semantics

### Portfolio outcomes
- **COMPLETED** — full evaluation, penalties/caps may apply.
- **VETOED** — governance veto; no penalties/caps applied.
- **FAILED** — technical failure.
- **SHORT_CIRCUITED** — policy prevention; holdings inherit SHORT_CIRCUITED.

### Holding outcomes
- **COMPLETED** — eligible for caps/penalties.
- **VETOED** — veto applied, no penalties/caps.
- **FAILED** — technical failure.
- **SHORT_CIRCUITED** — inherited from portfolio short-circuit.

## Emission Eligibility Matrix (DD-04/DD-08)

| Terminal Outcome | PortfolioCommitteePacket | HoldingPackets | FailedRunPacket | Hashes |
| --- | --- | --- | --- | --- |
| COMPLETED | ✅ | ✅ | ❌ | ✅ |
| VETOED | ✅ | ❌ | ❌ | ❌ |
| FAILED | ❌ | ❌ | ✅ | ❌ |
| SHORT_CIRCUITED | ✅ | ✅ (SHORT_CIRCUITED) | ❌ | ❌ |

Hashes are emitted **only** for COMPLETED outcomes per IMP-02.

## Test Coverage Mapping

### Governance precedence (DD-06)
- `tests/governance/test_precedence_order.py::test_dio_portfolio_veto_blocks_scoring_and_caps`
- `tests/governance/test_precedence_order.py::test_grra_short_circuit_prevents_penalties_and_caps`
- `tests/governance/test_precedence_order.py::test_risk_officer_veto_skips_penalties_and_caps`
- `tests/governance/test_precedence_order.py::test_caps_applied_before_penalties`
- `tests/governance/test_precedence_order.py::test_penalties_not_applied_to_dio_vetoed_holding`

### Emission eligibility (DD-04/DD-08)
- `tests/test_imp03_emission_and_thresholds.py::test_emission_completed_includes_hashes_and_holding_packets`
- `tests/test_imp03_emission_and_thresholds.py::test_failed_emits_failed_packet_only`

### Partial failure threshold (DD-08 G9)
- `tests/test_imp03_emission_and_thresholds.py::test_partial_failure_threshold_strictly_greater_than`
- `tests/test_guards_and_governance.py::test_partial_failure_threshold_strict_comparison`

### Provenance enforcement (DD-08 G2)
- `tests/test_imp03_emission_and_thresholds.py::test_provenance_guard_vetoes_unsourced_numeric_metrics`
- `tests/test_guards_and_governance.py::test_unsourced_numeric_metric_triggers_dio_veto`
