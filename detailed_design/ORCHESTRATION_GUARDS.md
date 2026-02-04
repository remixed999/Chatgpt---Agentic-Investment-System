# DD-07 — Orchestration Guards / Safety Rails (Portfolio-First)

## 1. Purpose
Guards are mandatory, deterministic gates that run before and around agent execution to prevent invalid outputs from reaching aggregation, enforce auditability and reproducibility, and ensure consistent portfolio vs holding handling.

Guiding principles:
- fail-loud (no silent assumptions)
- deterministic (same inputs => same decisions)
- portfolio-first
- governance cannot be bypassed

---

## 2. Guard Taxonomy (Authoritative)
Each guard below is authoritative and must declare scope, trigger condition, action, and required logged artifacts.

- G0: Input/Schema Guards
- G1: Identity & Portfolio Context Guards
- G2: Provenance Guards (“no invented numbers”)
- G3: Staleness & Hard-Stop Guards
- G4: Registry & Semantics Guards (HardStop vs PenaltyCritical; unknown vs NA)
- G5: Agent Output Conformance Guards
- G6: Governance Enforcement Guards (precedence)
- G7: Deterministic Ordering & Canonicalization Guards
- G8: Error Classification Guards (FAILED vs VETOED vs SHORT_CIRCUITED)
- G9: Partial Portfolio Run Guards (≤30% threshold, configurable later)
- G10: Emission Guards (what can be emitted, when)

Each guard specifies:
- Scope: portfolio-level or holding-level
- Trigger condition
- Action: STOP_RUN / VETO_HOLDING / FAIL_HOLDING / SHORT_CIRCUIT / CONTINUE_WITH_PENALTY / CONTINUE_WITH_WARNING
- Logged artifact(s): RunLog.ErrorRecord, veto flags, limitations

---

## 3. G0 — Input/Schema Guards (Phase 0)
Scope: portfolio-level.

Trigger conditions:
- PortfolioSnapshot, PortfolioConfig, RunConfig, seeded data fail schema validation.
- PortfolioSnapshot provided but PortfolioConfig.base_currency missing.
- RunConfig malformed (e.g., burn_rate_classification conflict).
- MetricValue has value != None and missing source_ref.

Actions:
- Schema validation failures => STOP_RUN with portfolio_run_outcome=FAILED.
- Missing base_currency with PortfolioSnapshot => portfolio_run_outcome=VETOED (DIO).
- MetricValue with value but no source_ref => portfolio_run_outcome=FAILED (input corruption).

Logged artifacts:
- Initialize RunLog with input_snapshot_hash.
- Record each schema failure as RunLog.ErrorRecord with error_type="schema_validation_error".

---

## 4. G1 — Identity & Portfolio Context Guards
Scope: holding-level for identity, portfolio-level for base currency.

Trigger conditions:
- InstrumentIdentity missing ticker, exchange, or currency.
- Portfolio present but base_currency missing.

Actions:
- Holding identity missing/malformed => holding_run_outcome=FAILED (technical), not VETOED.
- Missing base_currency when portfolio present => portfolio_run_outcome=VETOED (governance).

Logged artifacts:
- RunLog.ErrorRecord per holding with error_type="identity_validation_error".
- Veto flags and limitations for portfolio-level base_currency veto.

Notes:
- Exchange is required and treated as free-form string in MVP.

---

## 5. G2 — Provenance Guards (“No Invented Numbers”)
Scope: holding-level or portfolio-level depending on where the metric is used.

Trigger conditions:
- Any numeric metric used in scoring, penalties, caps, regime, or position sizing lacks SourceRef and is not explicitly marked as unknown or NA.
- Devil’s Advocate narrative includes numeric claims without SourceRef.

Actions:
- Unsourced numeric fact => DIO integrity veto (holding or portfolio depending on scope) with STOP_RUN for affected scope.
- Narrative without numbers may pass; numeric claims must be sourced.

Logged artifacts:
- DIOOutput.unsourced_numbers_detected=true.
- integrity_veto_triggered=true.
- RunLog.ErrorRecord identifying agent_name, field, and scope.

---

## 6. G3 — Staleness & Hard-Stop Guards
Scope: holding-level or portfolio-level depending on data type.

Trigger conditions:
- Data staleness exceeds penalty threshold or hard-stop threshold per mode.
- FX staleness exceeds hard-stop thresholds.

Actions:
- If hard-stop exceeded => DIO VETO (holding or portfolio depending on data type).
- If penalty threshold exceeded but within hard-stop => CONTINUE_WITH_PENALTY (Category B or E) and continue.
- Hard-stop supersedes penalties (no “stale AND penalty” once hard-stop is hit).

Logged artifacts:
- RunLog.ErrorRecord with error_type="staleness_hard_stop" or "staleness_penalty".
- Veto flags and limitations when hard-stop triggers.

Explicit hard-stop FX staleness:
- FAST >7 days
- DEEP >48 hours

---

## 7. G4 — Registry & Semantics Guards
Scope: holding-level unless specified otherwise.

Trigger conditions:
- HardStopFieldRegistry fields are missing or invalid.
- Burn-rate conditional rules violated.
- Unknown vs NA semantics inconsistent.

Actions:
- HardStopFieldRegistry enforced at governance level; identity schema violations are technical failures => FAILED.
- If is_burn_rate_company=true => cash/runway/burn are hard-stop.
- If not_applicable=true => cash/runway/burn ignored (no penalty, no veto).
- If is_burn_rate_company=true AND not_applicable=true => schema violation => FAILED.
- value=None + missing_reason + not_applicable=false => unknown (eligible for penalty if critical).
- not_applicable=true => never penalize that field.
- value=None + missing_reason=None + not_applicable=false => schema violation => FAILED.

Logged artifacts:
- RunLog.ErrorRecord with error_type="registry_semantics_error".
- Veto flags when hard-stop enforcement triggers governance.

---

## 8. G5 — Agent Output Conformance Guards
Scope: per agent (holding or portfolio-level depending on agent).

Trigger conditions:
- Agent output missing required AgentResult wrapper fields.
- confidence outside 0..1.
- status not in {"completed","failed","skipped"}.
- Agent crash detected.

Actions:
- Invalid AgentResult => FAIL_HOLDING or STOP_RUN depending on agent scope.
- Holding-level agent crash => holding_run_outcome=FAILED and continue to next holding.
- Portfolio-critical agent crash (GRRA, PSCC) => portfolio_run_outcome=FAILED and STOP_RUN.

Logged artifacts:
- RunLog.ErrorRecord with error_type="agent_output_conformance_error" or "agent_crash".
- Per-holding outcomes updated.

Deterministic execution:
- Agent execution order must be lexicographic by agent_name unless DD-03 flow specifies otherwise.

---

## 9. G6 — Governance Enforcement Guards (Precedence)
Scope: portfolio-level with holding inheritance.

Trigger conditions:
- Any governance action in the precedence stack triggers.

Actions:
- Enforce precedence exactly (from DD-06):
  1. DIO VETO
  2. GRRA SHORT_CIRCUIT
  3. Risk Officer VETO
  4. LEFO overrides/caps
  5. PSCC caps
  6. Risk Officer penalties
  7. Chair aggregation
- If a holding is VETOED at any veto stage, do not apply caps/penalties/score aggregation.
- If portfolio is SHORT_CIRCUITED, holdings inherit SHORT_CIRCUITED (unless DIO already vetoed portfolio earlier).
- Chair cannot override any enforcement.

Logged artifacts:
- RunLog.ErrorRecord noting enforcement stage and effect.
- Governance decision trail stored in RunLog and limitations.

---

## 10. G7 — Deterministic Ordering & Canonicalization Guards
Scope: portfolio-level with holding-level ordering.

Trigger conditions:
- Non-deterministic iteration detected (ordering differs from mandated sort).
- Canonicalization preconditions not met.

Actions:
- Holdings processed in stable sorted order by holding_id.
- Penalty items sorted by category, reason, source_agent.
- Agent outputs sorted by agent_name.
- Dict keys serialized with sort_keys=True for canonicalization.
- canonical_output_hash computed ONLY if portfolio_run_outcome=COMPLETED.
- Exclude equivalence fields exactly as HLD §6.
- If deterministic ordering cannot be guaranteed => portfolio_run_outcome=FAILED with error_type="determinism_violation".

Logged artifacts:
- RunLog.ErrorRecord for determinism violations.
- Canonicalization details in RunLog metadata.

---

## 11. G8 — Error Classification Guards
Scope: portfolio-level.

Trigger conditions:
- Outcome labels conflict or are ambiguous.

Actions:
- FAILED is technical/runtime fault.
- VETOED is governance enforcement.
- SHORT_CIRCUITED is policy prevention.
- RunLog.portfolio_run_outcome is single source of truth.
- PortfolioCommitteePacket mirrors RunLog outcome.

Logged artifacts:
- RunLog.ErrorRecord with error_type="outcome_conflict" if conflicts detected.

---

## 12. G9 — Partial Portfolio Run Guards (R20)
Scope: portfolio-level with holding-level outcomes.

Trigger conditions:
- Holdings are VETOED or FAILED above threshold.
- Portfolio-level DIO veto occurs.

Actions:
- Maintain per_holding_outcomes map always.
- Portfolio can be COMPLETED with some VETOED/FAILED holdings if failures ≤30%.
- If >30% holdings are VETOED or FAILED => portfolio_run_outcome=VETOED (unless already FAILED).
- If portfolio-level DIO veto occurs, ignore holding success and stop.

Logged artifacts:
- RunLog counts by outcome category and threshold used.
- Veto flags and limitations when threshold exceeded.

---

## 13. G10 — Emission Guards (What Outputs Are Allowed)
Scope: portfolio-level with holding-level packet rules.

Trigger conditions:
- portfolio_run_outcome in {COMPLETED, VETOED, SHORT_CIRCUITED, FAILED}.

Actions:
- If portfolio_run_outcome=COMPLETED:
  - emit PortfolioCommitteePacket + HoldingPackets + RunLog
- If VETOED:
  - emit minimal PortfolioCommitteePacket (veto note + limitations) + RunLog
  - do NOT emit canonical_output_hash
- If SHORT_CIRCUITED:
  - emit PortfolioCommitteePacket + HoldingPackets (all SHORT_CIRCUITED) + RunLog
  - do NOT emit recommendations or position sizing
- If FAILED:
  - emit FailedRunPacket + RunLog only

HoldingPacket rules:
- If holding FAILED, omit HoldingPacket (default).
- If holding VETOED, emit HoldingPacket with veto reason and limitations, no recommendation.

Logged artifacts:
- RunLog emission record with emitted artifacts list.

---

## 14. Acceptance Criteria
Document is complete if:
- all guards G0–G10 are defined with trigger/action/logging
- precedence matches DD-06 exactly
- determinism + canonical hash constraints are explicit
- no guard contradicts HLD outcome semantics
- emission rules are unambiguous and testable
