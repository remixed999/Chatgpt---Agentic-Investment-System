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

Governance decisions MUST be applied in this exact order:

1. **DIO VETO**
2. **GRRA SHORT_CIRCUIT**
3. **Risk Officer VETO**
4. **LEFO hard overrides and liquidity caps**
5. **PSCC concentration and structure caps**
6. **Risk Officer PENALTIES** (via DD-04)
7. **Chair aggregation and recommendation mapping**

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
(Reference: DD-04 — Penalty Engine)

Rules:
- penalties apply ONLY if:
  - NOT vetoed
  - NOT short-circuited
- penalties modify score, not outcome directly
- penalties must never “rescue” a vetoed holding

---

## 8. Outcome Resolution Matrix

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

## 9. Portfolio vs Holding Escalation

Rules:
- Holding veto does NOT automatically veto portfolio
- Portfolio veto overrides all holding outcomes
- Escalation thresholds (e.g., >30% holdings vetoed) are enforced by DD-07 guards

---

## 10. Determinism and Auditability

Requirements:
- every veto source recorded
- every override/cap recorded
- exactly ONE authoritative outcome per holding and portfolio
- governance decisions logged in RunLog

---

## 11. Non-Goals
This document does NOT define:
- scoring math
- penalty amounts
- optimization logic
- execution or trading logic

---

## 12. Acceptance Criteria

This document is complete if:
- precedence order matches DD-04 exactly
- Risk Officer veto vs penalty distinction is explicit
- Chair has no override authority
- no governance conflicts or ambiguities exist
- deterministic enforcement is guaranteed
