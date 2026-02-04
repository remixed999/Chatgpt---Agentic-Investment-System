# DD-06 — Governance Rules (Portfolio-First)

## 1. Purpose
Governance rules arbitrate conflicts between agents, determine veto vs override vs penalty application, enforce safety and integrity constraints, and produce deterministic outcomes.

Core principles:
- **portfolio-first**
- **hard-stops beat penalties**
- **veto > override > cap > penalty**
- **deterministic, auditable, reproducible**

This document defines **authority**, **precedence**, and **escalation logic** only.

---

## 2. Governance Actors and Authority Classes

### 2.1 Absolute Veto Authorities
These authorities can terminate evaluation immediately.

- **Data Integrity Officer (DIO)** — hard-stop integrity and freshness
- **Risk Officer** — conditional, holding-level safety veto

### 2.2 Policy Short-Circuit Authority
- **Global Risk Regime Architect (GRRA)**

### 2.3 Hard Override / Cap Authorities
- **Liquidity & Exit Feasibility Officer (LEFO)**
- **Portfolio Structure & Concentration Controller (PSCC)**

### 2.4 Advisory Authorities (No Enforcement Power)
- Fundamentals Agent
- Technical / Market Agent
- Devil’s Advocate

### 2.5 Aggregation Authority
- **Chair / Fund Manager**

**Invariant:**  
The Chair has **no override power**.

---

## 3. Absolute Precedence Order (AUTHORITATIVE)

Governance decisions MUST be applied in the exact order defined in Section 8 (Cross-DD Governance & Ordering Reconciliation).

**Invariant:**  
Lower-numbered rules ALWAYS supersede higher-numbered rules.

---

## 4. Veto Rules

### 4.1 DIO Veto (Hard-Stop)
Triggered by:
- missing HardStopFieldRegistry fields
- staleness beyond hard-stop thresholds
- unsourced numeric data
- unresolved integrity contradictions
- missing portfolio base_currency when required

Effects:
- holding_run_outcome or portfolio_run_outcome = **VETOED**
- penalties NOT applied
- caps NOT applied
- no score-based recommendations

---

### 4.2 Risk Officer Veto (Safety / Extreme Uncertainty)
Triggered by:
- extreme uncertainty + CRISIS regime
- penalties near total cap + low confidence
- Devil’s Advocate unresolved fatal risk
- systemic ambiguity deemed unsafe

Effects:
- holding_run_outcome = **VETOED**
- penalties discarded
- caps discarded
- veto reason logged

**Explicit distinction:**  
Risk Officer **VETO ≠ PENALTIES**

---

## 5. Short-Circuit Rules (GRRA)

Trigger:
- `do_not_trade_flag = true`

Effects:
- portfolio_run_outcome = **SHORT_CIRCUITED**
- holdings inherit SHORT_CIRCUITED
- no penalties
- no caps
- no recommendations

Clarification:
- **SHORT_CIRCUITED ≠ VETOED**
- indicates policy prevention, not failure

---

## 6. Override and Cap Rules

### 6.1 LEFO Overrides
- liquidity_grade ≤ 1 forces:
  - Avoid recommendation OR
  - near-zero position cap
- applies regardless of score

### 6.2 PSCC Caps
- single-name limits
- sector/theme concentration limits
- FX exposure limits
- enforced caps override score outcomes

**Invariant:**  
Overrides apply AFTER veto checks but BEFORE penalties and scoring.

---

## 7. Penalty Governance Integration
(Reference: DD-05 — Penalty Engine Specification)

Rules:
- penalties apply ONLY if:
  - NOT vetoed
  - NOT short-circuited
- penalties modify score, not outcome directly
- penalties must never “rescue” a vetoed holding

---

## 8. Cross-DD Governance & Ordering Reconciliation
This section reconciles governance precedence, guard actions, outcomes, and deterministic ordering across DD-04, DD-07, and DD-08 to provide a single authoritative reference point.

### 8.1 Governance Precedence Stack (Authoritative)
1. **DIO VETO**
2. **GRRA SHORT_CIRCUIT**
3. **Risk Officer VETO**
4. **LEFO hard overrides and liquidity caps**
5. **PSCC concentration and structure caps**
6. **Risk Officer PENALTIES** (via DD-05)
7. **Chair aggregation and recommendation mapping**

### 8.2 Guard Actions → Outcomes → Emission Eligibility
- **STOP_RUN (portfolio scope)** → `portfolio_run_outcome` is **FAILED** or **VETOED** based on guard classification; emission eligibility follows DD-04/DD-08 (FailedRunPacket only for FAILED; minimal PortfolioCommitteePacket for VETOED).
- **VETO_HOLDING** → `holding_run_outcome=VETOED`; HoldingPacket emitted with identity + veto reason only.
- **FAIL_HOLDING** → `holding_run_outcome=FAILED`; HoldingPacket omitted unless already emitted; outcome recorded in `per_holding_outcomes`.
- **SHORT_CIRCUIT** → `portfolio_run_outcome=SHORT_CIRCUITED`; holdings inherit SHORT_CIRCUITED; emit PortfolioCommitteePacket + HoldingPackets.
- **CONTINUE_WITH_PENALTY** → outcomes remain **COMPLETED**; penalties applied; full packet emission permitted.
- **CONTINUE_WITH_WARNING** → outcomes remain **COMPLETED**; no penalties; full packet emission permitted.

### 8.3 Deterministic Ordering Rule (Authoritative)
- Holdings ordered by `holding_id` (lexicographic).
- Agents ordered by `agent_name` (lexicographic).
- Penalties ordered by `category` → `reason` → `source_agent`.

### 8.4 Enforcement References
- **Governance precedence and outcomes:** DD-04 Orchestration Flow + DD-04 Orchestration State Machine.
- **Guard action enforcement:** DD-08 Orchestration Guards.
- **Ordering and hashing:** DD-07 Canonicalization Spec + DD-08 Deterministic Ordering Guard.
- **Emission eligibility:** DD-04 Orchestration Flow + DD-08 Emission Guards.

## 9. Outcome Resolution Matrix

### Portfolio-level outcomes:
- COMPLETED
- VETOED
- SHORT_CIRCUITED
- FAILED

### Holding-level outcomes:
- COMPLETED
- VETOED
- SHORT_CIRCUITED
- FAILED

Definitions:
- **FAILED** = technical/runtime failure
- **VETOED** = governance enforcement
- **SHORT_CIRCUITED** = policy prevention
- **COMPLETED** = evaluated with penalties/caps as applicable

---

## 10. Portfolio vs Holding Escalation

Rules:
- Holding veto does NOT automatically veto portfolio
- Portfolio veto overrides all holding outcomes
- Escalation thresholds (e.g., >30% holdings vetoed) are enforced by DD-08 guards

---

## 11. Determinism and Auditability

Requirements:
- every veto source recorded
- every override/cap recorded
- exactly ONE authoritative outcome per holding and portfolio
- governance decisions logged in RunLog

---

## 12. Non-Goals
This document does NOT define:
- scoring math
- penalty amounts
- optimization logic
- execution or trading logic

---

## 13. Acceptance Criteria

This document is complete if:
- precedence order matches DD-04 exactly
- Risk Officer veto vs penalty distinction is explicit
- Chair has no override authority
- no governance conflicts or ambiguities exist
- deterministic enforcement is guaranteed
