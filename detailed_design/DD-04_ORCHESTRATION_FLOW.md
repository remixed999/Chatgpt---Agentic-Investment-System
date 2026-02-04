# DD-04 — ORCHESTRATION_FLOW.md

## 1. Purpose

This document defines the orchestration flow and state transitions for the system, describing **what happens when** without prescribing implementation. It aligns to:

- **DD-01 (Schema Specifications):** All inputs/outputs named in this flow reference schemas defined in DD-01 and HLD v1.0 §5. 
- **DD-02 (Data Contracts):** Contract boundaries, required payloads, and portfolio-vs-holding semantics govern the flow described here.
- **HLD v1.0 §4–§5:** Execution phases, run outcomes, and packet eligibility are derived from HLD orchestration and data model requirements.

---

## 2. Orchestration Principles

1. **Portfolio-first execution:** Portfolio-level context is established before holding-level evaluation, and portfolio-level outcomes gate final outputs.
2. **Deterministic state transitions:** All transitions are explicit and must map to a defined orchestration state and run outcome.
3. **Holding-level isolation:** Each holding’s evaluation is independent; a failure in one holding does not invalidate other holdings unless explicitly noted at the portfolio level.
4. **Non-mutating contracts:** Inputs and agent outputs are treated as immutable once emitted; orchestration only routes and aggregates per DD-02.
5. **Explicit short-circuiting:** When eligibility conditions are met (e.g., VETOED, FAILED, SHORT_CIRCUITED), the flow terminates deterministically with specified outputs.
6. **Schema-locked outputs:** Orchestration may emit only the schema-defined packets and must honor presence/absence rules by run outcome.
7. **PSCC singular execution:** PSCC executes exactly once per portfolio run after holding-level evaluation completes and before aggregation readiness.

---

## 3. Execution Phases (High-Level)

### Phase 0 — Intake & Canonicalization Eligibility
**Purpose:** Establish the run context and eligibility to proceed with portfolio and holding evaluation.

**Inputs (schemas):**
- PortfolioSnapshot
- PortfolioConfig
- RunConfig

**Outputs (schemas):**
- RunLog (initialized)
- Holding eligibility status list (internal orchestration state only; no new schema)

**Eligible outcomes:** CONTINUE / SHORT-CIRCUIT / FAIL

---

### Phase 1 — Data Integrity Evaluation (DIO)
**Purpose:** Evaluate data integrity and hard-stop eligibility at portfolio and holding scope.

**Inputs (schemas):**
- PortfolioSnapshot
- PortfolioConfig
- RunConfig
- Holding-level inputs (embedded InstrumentIdentity)

**Outputs (schemas):**
- DIOOutput (portfolio-level where applicable)
- DIOOutput (holding-level, per holding)
- RunLog (updated)

**Eligible outcomes:** CONTINUE / SHORT-CIRCUIT / FAIL

---

### Phase 2 — Portfolio Context Evaluation (GRRA)
**Purpose:** Establish macro regime context and portfolio pre-flight signals that may gate holding execution.

**Inputs (schemas):**
- PortfolioSnapshot
- PortfolioConfig
- RunConfig

**Outputs (schemas):**
- GRRAOutput
- RunLog (updated)

**Eligible outcomes:** CONTINUE / SHORT-CIRCUIT / FAIL

---

### Phase 3 — Holding-Level Analytical Evaluation
**Purpose:** Produce holding-level analytical outputs (fundamentals, technical, liquidity, risk).

**Inputs (schemas):**
- Holding-level inputs (InstrumentIdentity + MetricValue-bearing data)
- PortfolioConfig (as required by contract)

**Outputs (schemas):**
- AgentResult-based outputs (Fundamentals, Technical, LEFO, Risk Officer, optional agents)
- HoldingPacket (per holding, if eligible)
- RunLog (updated)

**Eligible outcomes:** CONTINUE / SHORT-CIRCUIT / FAIL (per holding)

---

### Phase 3B — Portfolio Structure & Concentration Controls (PSCC)
**Purpose:** Evaluate portfolio structure and concentration caps after holding-level outputs are complete and before aggregation.

**Inputs (schemas):**
- PortfolioSnapshot
- PortfolioConfig
- Holding-level outputs (read-only)

**Outputs (schemas):**
- PSCCOutput
- RunLog (updated)

**Eligible outcomes:** CONTINUE / FAIL

---

### Phase 4 — Risk Aggregation
**Purpose:** Aggregate holding-level risk and portfolio context into a portfolio-level risk view.

**Inputs (schemas):**
- PortfolioSnapshot
- PortfolioConfig
- GRRAOutput
- PSCCOutput
- Holding-level outputs and outcomes

**Outputs (schemas):**
- Risk Officer Output (portfolio-level, if defined by schema)
- RunLog (updated)

**Eligible outcomes:** CONTINUE / FAIL

---

### Phase 5 — Chair Aggregation & Packet Assembly
**Purpose:** Assemble PortfolioCommitteePacket and finalize HoldingPacket(s) per outcome eligibility.

**Inputs (schemas):**
- PortfolioSnapshot
- PortfolioConfig
- RunConfig
- GRRAOutput
- PSCCOutput
- Holding-level outputs and outcomes

**Outputs (schemas):**
- PortfolioCommitteePacket (if eligible)
- HoldingPacket(s) (if eligible)
- RunLog (updated)

**Eligible outcomes:** CONTINUE / SHORT-CIRCUIT / FAIL

---

### Phase 6 — Finalization & Output Emission
**Purpose:** Finalize run outcomes and emit the correct output packet(s) based on terminal state.

**Inputs (schemas):**
- PortfolioCommitteePacket (if eligible)
- HoldingPacket(s) (if eligible)
- FailedRunPacket (if eligible)
- RunLog

**Outputs (schemas):**
- PortfolioCommitteePacket
- HoldingPacket(s)
- FailedRunPacket
- RunLog

**Eligible outcomes:** CONTINUE / SHORT-CIRCUIT / FAIL (terminal)

---

## 4. State Machine Overview

**Named orchestration states:**
- INIT
- INTAKE_COMPLETE
- PORTFOLIO_INTEGRITY_READY
- PORTFOLIO_CONTEXT_READY
- HOLDING_EVALUATION_IN_PROGRESS
- HOLDING_EVALUATION_COMPLETE
- AGGREGATION_READY
- FINALIZATION_READY
- COMPLETED (terminal)
- VETOED (terminal)
- FAILED (terminal)
- SHORT_CIRCUITED (terminal)

**Allowed transitions:**
- INIT → INTAKE_COMPLETE
- INTAKE_COMPLETE → PORTFOLIO_INTEGRITY_READY | FAILED | VETOED
- PORTFOLIO_INTEGRITY_READY → PORTFOLIO_CONTEXT_READY | SHORT_CIRCUITED | FAILED | VETOED
- PORTFOLIO_CONTEXT_READY → HOLDING_EVALUATION_IN_PROGRESS | SHORT_CIRCUITED | FAILED
- HOLDING_EVALUATION_IN_PROGRESS → HOLDING_EVALUATION_COMPLETE | FAILED
- HOLDING_EVALUATION_COMPLETE → AGGREGATION_READY | FAILED | VETOED
- AGGREGATION_READY → FINALIZATION_READY | FAILED | VETOED
- FINALIZATION_READY → COMPLETED | VETOED | FAILED | SHORT_CIRCUITED

**Terminal states:** COMPLETED, VETOED, FAILED, SHORT_CIRCUITED.

---

## 5. Portfolio-Level Orchestration Flow

1. **Portfolio Intake Order:** PortfolioSnapshot → PortfolioConfig → RunConfig are required before any portfolio-level agent runs.
2. **Portfolio-Level Agents:** DIO (portfolio integrity) and GRRA (macro regime) are evaluated before holding-level agents.
3. **PSCC Timing:** PSCC executes once after all holding-level analytical outputs are complete and before any aggregation; aggregation cannot proceed until PSCCOutput is available.
4. **Portfolio Failure Impact:**
   - Portfolio-level FAILED or VETOED terminates the run and prevents holding-level evaluation outputs from being emitted except where explicitly allowed by DD-02.
   - Portfolio-level SHORT_CIRCUIT ends the run with appropriate packets reflecting short-circuit status.
5. **PortfolioCommitteePacket Eligibility:**
   - Eligible when portfolio_run_outcome is COMPLETED, VETOED, or SHORT_CIRCUITED.
   - Not eligible when portfolio_run_outcome is FAILED (FailedRunPacket only).
6. **Per-Holding Outcomes:** PortfolioCommitteePacket must enumerate per_holding_outcomes even when holdings are failed or vetoed.

---

## 6. Holding-Level Orchestration Flow

1. **Independent Evaluation:** Each holding is evaluated independently once portfolio context is ready, using its own InstrumentIdentity and MetricValue-bearing inputs.
2. **Holding Short-Circuit Rules:**
   - A holding may be SHORT_CIRCUITED due to portfolio-level short-circuiting, or due to holding-level veto conditions.
3. **Partial HoldingPacket Population:**
   - When holding_run_outcome is FAILED or VETOED, HoldingPacket includes required identity fields and outcome, and omits scorecard/recommendation fields per DD-02.
4. **Isolation Guarantees:**
   - No holding’s outcome may mutate or invalidate another holding’s outputs; aggregation only reflects outcomes already emitted for each holding.

---

## 7. Short-Circuit Rules

**VETO eligibility (immediate termination at applicable scope):**
- Missing portfolio-level hard-stop fields (e.g., base_currency when required).
- DIO integrity veto indicators at portfolio or holding scope.

**FAILED eligibility (technical or contract failure):**
- Missing hard-stop identity fields in InstrumentIdentity (holding-level, technical failure per DD-02 Outcome Classification Rule).
- Missing or malformed required schema payloads that prevent interpretation.
- Semantically invalid MetricValue or SourceRef usage per DD-01.
- Unrecoverable portfolio-level agent or orchestration failure.

**Partial continuation eligibility:**
- Holding-level failures do not automatically fail the portfolio run; they are recorded per holding and included in portfolio outcomes.
- Portfolio-level SHORT_CIRCUIT may still emit holding packets marked SHORT_CIRCUITED.

(Eligibility rules only; no enforcement logic.)
Outcome classification for identity omissions and base currency vetoes is authoritative in DD-02 §7 (Outcome Classification Rule).

---

## 8. VETOED vs FAILED Resolution Order

1. **Precedence:**
   - If a VETO-eligible condition is detected before a FAILED condition at the same scope, the terminal state is VETOED.
   - If a FAILED condition is detected first and prevents evaluation of VETO eligibility, the terminal state is FAILED.
2. **Conflict Resolution:**
   - Portfolio-level VETO supersedes holding-level outcomes in terms of final portfolio_run_outcome, while holding outcomes are still reported where allowed.
   - Holding-level VETO applies only to that holding unless a portfolio-level VETO condition is also present.
3. **Terminal Behavior:**
   - VETOED and FAILED are terminal and do not transition back to non-terminal states.

---

## 9. Output Eligibility Matrix

| Orchestration State | PortfolioRunOutcome | HoldingRunOutcome | PortfolioCommitteePacket | HoldingPacket | FailedRunPacket |
|---|---|---|---|---|---|
| COMPLETED | COMPLETED | COMPLETED | Permitted | Permitted | Not permitted |
| COMPLETED | COMPLETED | FAILED | Permitted | Permitted (partial) | Not permitted |
| COMPLETED | COMPLETED | VETOED | Permitted | Permitted (partial) | Not permitted |
| VETOED | VETOED | VETOED / FAILED / SHORT_CIRCUITED | Permitted (minimal) | Permitted only if already emitted | Not permitted |
| SHORT_CIRCUITED | SHORT_CIRCUITED | SHORT_CIRCUITED | Permitted | Permitted | Not permitted |
| FAILED | FAILED | FAILED / UNKNOWN | Not permitted | Not permitted (unless already emitted) | Permitted |

---

## 10. Non-Goals

This document does NOT define:
- Validation logic or enforcement algorithms.
- Penalty calculations or scoring logic.
- Implementation details, orchestration engines, queues, or APIs.
- Any schema changes or new schemas beyond DD-01 and HLD v1.0 §5.
- Runtime data storage, persistence, or telemetry formats.

---

## 11. Traceability

| Section | HLD v1.0 Reference | DD-01 / DD-02 Dependency |
|---|---|---|
| 1. Purpose | §4, §5 | DD-01 schemas; DD-02 contracts |
| 2. Orchestration Principles | §4 | DD-02 scope and immutability |
| 3. Execution Phases | §4 | DD-01 schema references; DD-02 contract boundaries |
| 4. State Machine Overview | §4 (Run Outcome Semantics) | DD-02 outcome semantics |
| 5. Portfolio-Level Flow | §4 (Portfolio-first) | DD-02 portfolio contracts |
| 6. Holding-Level Flow | §4 (Holding loop) | DD-02 holding isolation |
| 7. Short-Circuit Rules | §4, §7 | DD-02 contract failure semantics |
| 8. VETOED vs FAILED Resolution Order | §4, §7 | DD-02 outcomes |
| 9. Output Eligibility Matrix | §5 (PortfolioCommitteePacket, HoldingPacket, FailedRunPacket) | DD-02 packet eligibility |
| 10. Non-Goals | §1 (Non-goals) | DD-01/DD-02 scope exclusions |

---

## 12. Status

STATUS: DD-04 COMPLETE — Awaiting transition to DD-04_ORCHESTRATION_STATE_MACHINE.md
