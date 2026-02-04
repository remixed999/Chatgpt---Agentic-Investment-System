# Design Risk and Issue Register — FINAL LOCKED VERSION

## 1. Purpose
This document records the **final, locked** risk and issue disposition for the Detailed Design. All items from the prior register are closed as **RESOLVED** or **ACCEPTED**. No historical statuses are retained.

## 2. Design Risk Register (Final)

### R-01 — Canonicalization ordering depends on runtime timestamps
- **Status:** RESOLVED
- **Resolution Summary:** Canonicalization explicitly excludes veto logs and runtime timestamps from decision-significant payloads; timestamp ordering is limited to logging only (DD-07).

### R-02 — Partial failure threshold comparison rule is under-specified
- **Status:** RESOLVED
- **Resolution Summary:** Explicit numerator/denominator, rounding policy, comparison operator, and evaluation state are defined in DD-04 and DD-08.

## 3. Design Issue Log (Final)

### I-01 — AgentResult contract fields are inconsistent across DD-02 and DD-03
- **Status:** RESOLVED
- **Resolution Summary:** A single canonical AgentResult schema is defined in DD-01/DD-02 and DD-03 references it without conflicting fields.

### I-02 — HoldingPacket emission rules for FAILED holdings conflict
- **Status:** RESOLVED
- **Resolution Summary:** FAILED holdings emit a minimal HoldingPacket with identity, outcome, and error classification in limitations; scorecards/recommendations are omitted across DD-02/DD-04/DD-08/DD-09.

### I-03 — Debug-mode handling of unsourced numbers is inconsistent
- **Status:** RESOLVED
- **Resolution Summary:** Debug mode is explicitly logging-only and does not alter DIO veto or penalty behavior (DD-05, DD-09 aligned).

### I-04 — Registry and configuration schemas referenced but not specified
- **Status:** RESOLVED
- **Resolution Summary:** ConfigSnapshot, HardStopFieldRegistry, and PenaltyCriticalFieldRegistry are defined in DD-01 and referenced consistently.

### I-05 — PortfolioSnapshot fixture definition conflicts with PortfolioConfig contract
- **Status:** RESOLVED
- **Resolution Summary:** Fixtures now place base_currency in PortfolioConfig, aligned with DD-02.

## 4. Accepted Risks
None. All prior risks are resolved in this lock.

## 5. Assurance Summary
- **Overall design risk posture:** LOW
- **Design lock statement:** “This design is locked and approved for implementation. Further changes require a new design change request.”
