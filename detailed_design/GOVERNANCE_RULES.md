# DD-06 — Governance Rules (Portfolio-First)

## 1. Purpose
Governance rules arbitrate conflicts between agents, determine veto vs override vs penalty application, enforce safety/integrity/regime constraints, and produce deterministic outcomes.

Core principles:
- portfolio-first
- hard-stops beat penalties
- veto > override > cap > penalty
- deterministic, auditable, reproducible

---

## 2. Governance Actors and Authority Classes

### 2.1 Absolute Veto Authorities
These immediately terminate evaluation for a holding or portfolio.

- Data Integrity Officer (DIO)
- Risk Officer (conditional, holding-level only)

### 2.2 Policy Short-Circuit Authority
- Global Risk Regime Architect (GRRA)

### 2.3 Hard Override / Cap Authorities
- Liquidity & Exit Feasibility Officer (LEFO)
- Portfolio Structure & Concentration Controller (PSCC)

### 2.4 Advisory Authorities
- Fundamentals Agent
- Technical Agent
- Devil’s Advocate

### 2.5 Aggregation Authority (No Override Power)
- Chair / Fund Manager

Chair cannot override vetoes, short-circuits, caps, or overrides.

---

## 3. Absolute Precedence Order (AUTHORITATIVE)

1. DIO VETO  
2. GRRA SHORT_CIRCUIT  
3. Risk Officer VETO  
4. LEFO hard overrides and liquidity caps  
5. PSCC concentration and structure caps  
6. Risk Officer PENALTIES (Category A–F via DD-05)  
7. Chair aggregation and recommendation mapping  

Invariant: Lower-numbered rules ALWAYS supersede higher-numbered rules.

---

## 4. Veto Rules

### 4.1 DIO Veto (Hard-Stop)
Triggers include:
- missing HardStopFieldRegistry fields
- staleness beyond hard-stop thresholds
- integrity failures (unsourced numbers, contradictions)
- missing portfolio base_currency when required

Effects:
- holding_run_outcome or portfolio_run_outcome = VETOED
- no penalties applied
- no caps applied
- no score-based recommendations

---

### 4.2 Risk Officer Veto (Safety / Extreme Uncertainty)
Triggers include:
- extreme uncertainty + CRISIS regime
- penalties near total cap + low confidence
- unresolved fatal risk signals

Effects:
- holding_run_outcome = VETOED
- penalties discarded
- caps discarded
- veto reason logged

Explicit distinction:
Risk Officer VETO ≠ Risk Officer PENALTIES

---

## 5. Short-Circuit Rules (GRRA)

- do_not_trade flag behavior
- portfolio-wide SHORT_CIRCUITED outcome
- inheritance to all holdings

Effects:
- no recommendations
- no penalties
- no caps
- informational packets only

Clarify:
SHORT_CIRCUITED ≠ VETOED

---

## 6. Override and Cap Rules

### 6.1 LEFO Overrides
- liquidity_grade ≤1 forces Avoid or near-zero cap
- applies regardless of score

### 6.2 PSCC Caps
- single-name, sector, theme, FX caps
- downgrade or cap position sizing
- advisory to Chair but enforced

Clarify:
Overrides apply AFTER veto checks but BEFORE penalties and scoring.

---

## 7. Penalty Governance Integration

Reference: DD-05 Penalty Engine Spec.

Rules:
- penalties only apply if NOT vetoed or short-circuited
- penalties affect score, not outcome directly
- penalties never “rescue” vetoed holdings

---

## 8. Outcome Resolution Matrix

Portfolio-level:
- COMPLETED
- VETOED
- SHORT_CIRCUITED
- FAILED

Holding-level:
- COMPLETED
- VETOED
- SHORT_CIRCUITED
- FAILED

Clarify:
- FAILED = technical/runtime failure
- VETOED = governance enforcement
- SHORT_CIRCUITED = policy prevention
- COMPLETED = evaluated with possible penalties/caps

---

## 9. Portfolio vs Holding Escalation Rules

Define:
- per-holding veto does not automatically veto portfolio
- portfolio veto triggers (e.g., >30% holdings vetoed/failed)
- escalation precedence

---

## 10. Determinism and Auditability

Rules:
- governance decisions must be logged
- veto source agent always recorded
- no ambiguous outcomes
- exactly one authoritative run outcome

---

## 11. Non-Goals

Explicitly exclude:
- scoring math
- penalty amounts
- portfolio optimization logic
- execution logic

---

## 12. Acceptance Criteria

File is complete if:
- precedence order matches DD-05 exactly
- Risk Officer veto vs penalty distinction is explicit
- no agent is granted ambiguous override power
- Chair is explicitly non-overriding
- governance logic is deterministic and conflict-free
