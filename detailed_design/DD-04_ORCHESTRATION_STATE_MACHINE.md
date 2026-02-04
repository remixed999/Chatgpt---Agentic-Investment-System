# DD-04 — Orchestration State Machine

## 1. Purpose
This document defines the deterministic orchestration state machine that governs portfolio-first execution, including state definitions, allowed transitions, terminal outcomes, and emission eligibility. It aligns with DD-04 orchestration flow phases and DD-06 governance precedence without prescribing implementation details.

---

## 2. State Model Overview
The orchestration state machine operates at two scopes:
- **Portfolio scope** — the single run-level state machine.
- **Holding scope** — per-holding evaluation state machines that inherit portfolio-level governance outcomes.

### 2.1 Portfolio State List
- **INIT**
- **INTAKE_COMPLETE**
- **PORTFOLIO_INTEGRITY_READY**
- **PORTFOLIO_CONTEXT_READY**
- **HOLDING_EVALUATION_IN_PROGRESS**
- **HOLDING_EVALUATION_COMPLETE**
- **AGGREGATION_READY**
- **FINALIZATION_READY**
- **COMPLETED** (terminal)
- **VETOED** (terminal)
- **FAILED** (terminal)
- **SHORT_CIRCUITED** (terminal)

### 2.2 Holding State List
- **HOLDING_PENDING**
- **HOLDING_IDENTITY_VALIDATED**
- **HOLDING_DATA_INTEGRITY_READY**
- **HOLDING_EVALUATION_IN_PROGRESS**
- **HOLDING_EVALUATION_COMPLETE**
- **HOLDING_COMPLETED** (terminal)
- **HOLDING_VETOED** (terminal)
- **HOLDING_FAILED** (terminal)
- **HOLDING_SHORT_CIRCUITED** (terminal)

---

## 3. Portfolio-Level Transitions (Deterministic)
Transitions are evaluated in the order defined below; the first applicable terminal condition ends the run.

1. **INIT → INTAKE_COMPLETE**
   - Trigger: PortfolioSnapshot + PortfolioConfig + RunConfig received and schema validation passes.
   - Failure path: schema failure → **FAILED**.

2. **INTAKE_COMPLETE → PORTFOLIO_INTEGRITY_READY**
   - Trigger: Portfolio-level DIO inputs available.
   - Veto path: missing portfolio `base_currency` when PortfolioSnapshot is present → **VETOED** (per DD-02 Outcome Classification Rule).
   - Failure path: malformed portfolio inputs that prevent interpretation → **FAILED**.

3. **PORTFOLIO_INTEGRITY_READY → PORTFOLIO_CONTEXT_READY**
   - Trigger: Portfolio-level integrity checks complete with no veto.
   - Veto path: DIO integrity veto (hard-stop) → **VETOED**.
   - Failure path: portfolio-level DIO failure → **FAILED**.
   - Short-circuit path: GRRA `do_not_trade_flag=true` → **SHORT_CIRCUITED**.

4. **PORTFOLIO_CONTEXT_READY → HOLDING_EVALUATION_IN_PROGRESS**
   - Trigger: Portfolio context outputs available and no terminal governance action triggered.

5. **HOLDING_EVALUATION_IN_PROGRESS → HOLDING_EVALUATION_COMPLETE**
   - Trigger: All holdings have reached terminal holding outcomes.
   - Failure path: portfolio-critical agent crash (GRRA/PSCC) → **FAILED**.

6. **HOLDING_EVALUATION_COMPLETE → AGGREGATION_READY**
   - Trigger: All per-holding outcomes recorded; aggregation inputs available.
   - Veto path: portfolio-level veto detected post-holding evaluation (Risk Officer veto) → **VETOED**.
   - Failure path: aggregation inputs invalid → **FAILED**.

7. **AGGREGATION_READY → FINALIZATION_READY**
   - Trigger: Aggregation outputs ready and consistent.
   - Failure path: non-deterministic ordering detected → **FAILED**.

8. **FINALIZATION_READY → COMPLETED | VETOED | FAILED | SHORT_CIRCUITED**
   - Trigger: outcome resolution per DD-06 precedence and DD-08 guard actions.

---

## 4. Holding-Level Transitions (Deterministic)
Holding states are evaluated per holding in stable order by `holding_id` (see Section 7).

1. **HOLDING_PENDING → HOLDING_IDENTITY_VALIDATED**
   - Trigger: Holding InstrumentIdentity present.
   - Failure path: missing `ticker`, `exchange`, or `currency` → **HOLDING_FAILED** (technical, per DD-02 Outcome Classification Rule).

2. **HOLDING_IDENTITY_VALIDATED → HOLDING_DATA_INTEGRITY_READY**
   - Trigger: DIO holding inputs available.
   - Veto path: DIO integrity veto (hard-stop) → **HOLDING_VETOED**.
   - Failure path: malformed holding inputs preventing interpretation → **HOLDING_FAILED**.

3. **HOLDING_DATA_INTEGRITY_READY → HOLDING_EVALUATION_IN_PROGRESS**
   - Trigger: Holding-level agents scheduled; portfolio not short-circuited.
   - Short-circuit path: portfolio run short-circuited → **HOLDING_SHORT_CIRCUITED**.

4. **HOLDING_EVALUATION_IN_PROGRESS → HOLDING_EVALUATION_COMPLETE**
   - Trigger: all required holding-level agent outputs collected.
   - Failure path: holding-level agent crash → **HOLDING_FAILED**.

5. **HOLDING_EVALUATION_COMPLETE → HOLDING_COMPLETED | HOLDING_VETOED | HOLDING_FAILED | HOLDING_SHORT_CIRCUITED**
   - Trigger: governance precedence applied (DD-06). Risk Officer veto → **HOLDING_VETOED**.

---

## 5. Terminal Outcomes and Emission Eligibility
Terminal states map to output eligibility as follows:

### Portfolio Outcomes
- **COMPLETED** → emit PortfolioCommitteePacket + eligible HoldingPackets + RunLog.
- **VETOED** → emit minimal PortfolioCommitteePacket (veto reason + limitations) + RunLog; no canonical hash.
- **SHORT_CIRCUITED** → emit PortfolioCommitteePacket + HoldingPackets (all SHORT_CIRCUITED) + RunLog.
- **FAILED** → emit FailedRunPacket + RunLog only.

### Holding Outcomes
- **HOLDING_COMPLETED** → emit full HoldingPacket.
- **HOLDING_VETOED** → emit HoldingPacket with identity + veto reason + limitations; omit recommendations/scorecard per DD-02.
- **HOLDING_FAILED** → omit HoldingPacket unless it was already emitted prior to failure; outcome recorded in `per_holding_outcomes`.
- **HOLDING_SHORT_CIRCUITED** → emit HoldingPacket with SHORT_CIRCUITED outcome; no recommendations.

---

## 6. Invariants
- **Governance precedence:** DIO veto > GRRA short-circuit > Risk Officer veto > LEFO/PSCC caps > penalties > chair aggregation (DD-06).
- **Hard-stops beat penalties:** once a hard-stop veto is triggered, penalties are not applied.
- **Portfolio-first:** portfolio terminal outcome gates final emissions; holdings inherit portfolio short-circuit where applicable.
- **Single authoritative outcome:** exactly one terminal outcome per portfolio run and per holding.

---

## 7. Determinism Requirements
- **Ordering:** holdings processed in stable lexicographic order by `holding_id`; agent outputs ordered by `agent_name`; penalties ordered by `category` → `reason` → `source_agent`.
- **No parallel nondeterminism:** parallel execution must not affect ordering or outcome resolution.
- **Canonicalization:** output hashes are computed only when `portfolio_run_outcome = COMPLETED` (DD-07).

---

## 8. Traceability
- **DD-04 Orchestration Flow:** phase alignment and transition triggers.
- **DD-06 Governance Rules:** precedence stack and veto/short-circuit semantics.
- **DD-08 Orchestration Guards:** guard triggers and outcome enforcement.
- **DD-07 Canonicalization Spec:** deterministic ordering and hashing constraints.
- **DD-09 Test Fixtures:** fixture traceability for terminal outcomes and ordering.
