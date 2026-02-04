# DD-10 — Test Strategy (Portfolio-First, Deterministic, Governed)

## 1. Purpose & Objectives
This test strategy defines the **authoritative testing approach** for the Agentic Investment System and **constrains deployment behavior**: code may only be promoted when required tests pass. The objectives are to ensure:

- **Deterministic behavior** across identical runs (replayable outcomes and hashes).
- **Governance enforcement is never bypassed**, with precedence order enforced as **veto > short-circuit > override > cap > penalty**.
- **Canonicalization and hashing are reproducible** across environments.
- **Portfolio- and holding-level outcomes are correct**, including partial portfolio completion rules.
- **Deployment and testing are fully aligned**, with tests acting as hard gates for promotion.

**Alignment Sources**: HLD v1.0 and DD-01 through DD-09 are authoritative; no new architecture is introduced here.

---

## 2. Testing Scope
The strategy covers all completed Detailed Design documents and maps each DD to at least one test class:

- **DD-01 Schema Specifications** → *Schema Validation Unit Tests* and *Contract Tests*.
- **DD-02 Data Contracts** → *Contract Tests* and *Provenance/No-Invented-Numbers Tests*.
- **DD-03 Agent Interface Contracts** → *Agent Envelope Contract Tests* and *Agent Conformance Tests*.
- **DD-04 Orchestration Flow & State Machine** → *Deterministic Replay Tests* and *Outcome Classification Tests*.
- **DD-05 Penalty Engine Spec** → *Penalty Computation Unit Tests* and *Portfolio Outcome Tests*.
- **DD-06 Governance Rules** → *Governance Enforcement Tests* and *Precedence Tests*.
- **DD-07 Canonicalization Spec** → *Canonicalization/Hash Determinism Tests*.
- **DD-08 Orchestration Guards** → *Guard Enforcement Tests* and *Failure Classification Tests*.
- **DD-09 Test Fixture Specifications** → *Fixture Compliance Tests* and *Deterministic Fixture Replay Tests*.

Scope explicitly includes:
- Schema validation and data contract compliance.
- Deterministic ordering, canonicalization, and hash stability.
- Governance enforcement (veto, short-circuit, overrides, caps, penalties).
- Portfolio-first orchestration outcomes, including partial portfolio completion rules.
- Guard rails for provenance, staleness, registry semantics, and emission rules.

Out of scope for testing (by design): free-form narrative quality and stylistic text (disclaimers, limitations), except where a field’s **presence** is required by schema or governance rules.

---

## 3. Test Levels (Authoritative)
Each test level defines purpose, inputs, expected outputs, and blocking behavior.

### 3.1 Unit Tests
**Purpose:** Validate deterministic behavior of individual components (schemas, penalty math, ordering, canonicalization logic).

**Inputs:** Single fixtures or minimal object graphs, strictly from DD-09 fixtures.

**Expected Outputs:**
- Schema validation pass/fail.
- Penalty calculation results and caps (DEEP/FAST).
- Deterministic ordering of lists and dictionaries.

**Blocking:** **Blocking** for any failure; unit failures prevent all promotions.

### 3.2 Contract Tests
**Purpose:** Enforce data contracts between agents and orchestrator, including required fields, provenance, and permitted values.

**Inputs:** AgentResult envelopes, MetricValue records, SourceRef metadata, registry snapshots.

**Expected Outputs:**
- AgentResult conformance to schema and constraints.
- Provenance requirements enforced for numeric values.
- HardStop vs PenaltyCritical registry rules respected.

**Blocking:** **Blocking** for missing required fields, invalid semantics, or provenance violations.

### 3.3 Deterministic Replay Tests
**Purpose:** Verify that identical logical inputs produce identical outputs and hashes, independent of ordering or runtime metadata.

**Inputs:** Paired fixture runs with:
- Different ordering of holdings/agents/penalties.
- Different runtime timestamps and run IDs.

**Expected Outputs:**
- Canonical hashes identical for logically identical inputs.
- Canonical hashes differ only when decision-significant fields differ.

**Blocking:** **Blocking** for any mismatch or environment-sensitive variance.

### 3.4 Governance Enforcement Tests
**Purpose:** Ensure governance precedence and guard enforcement are applied deterministically and cannot be bypassed.

**Inputs:** Fixture-driven scenarios including DIO veto, GRRA short-circuit, Risk Officer veto, LEFO overrides, PSCC caps.

**Expected Outputs:**
- Outcome classification aligns with governance precedence (veto > short-circuit > override > cap > penalty).
- No penalties/caps applied once vetoed or short-circuited.

**Blocking:** **Blocking** for any precedence violation or inconsistent outcomes.

### 3.5 Portfolio Outcome Tests
**Purpose:** Validate portfolio-first outcomes, partial failure thresholds, and portfolio/holding consistency.

**Inputs:** Portfolio fixtures (N>=1) with controlled mixes of COMPLETED/VETOED/FAILED.

**Expected Outputs:**
- Portfolio_run_outcome correctly computed.
- Per-holding outcomes preserved and emitted correctly.
- Partial failure threshold enforced deterministically.

**Blocking:** **Blocking** for incorrect portfolio outcome or inconsistent emission rules.

### 3.6 Regression & Non-Regression Tests
**Purpose:** Prevent drift in deterministic outputs, penalty totals, and hashes across releases.

**Inputs:** Baseline fixtures with expected outputs and canonical hashes (DD-09 expected fixtures).

**Expected Outputs:**
- No change in expected outputs or hashes unless explicitly versioned.

**Blocking:**
- **Blocking** for any regression in decision-significant outputs.
- **Non-blocking** only for documentation-only changes or narrative-only fields explicitly excluded from hashes.

---

## 4. Fixture-Driven Testing
All non-trivial tests **must** use deterministic fixtures defined in DD-09.

**Mandates:**
- **No runtime-generated data** in tests.
- **All timestamps are fixed** ISO8601 UTC values.
- **All numeric values are sourced** and reference deterministic SourceRef metadata.

**Fixture Versioning & Reuse:**
- Fixtures are versioned via metadata (`fixture_id`, `version`, `created_at_utc`).
- Any update to fixtures requires a documented version increment and baseline update for expected hashes.
- Fixtures are immutable once used for released baselines; changes require explicit governance review and release notes.

---

## 5. Governance & Failure Handling
Tests must enforce governance outcomes and failure classifications exactly:

### 5.1 Expected Behavior to Test
- **VETOED** outcomes: DIO or Risk Officer veto blocks scoring, penalties, caps, and recommendations.
- **SHORT_CIRCUITED** outcomes: GRRA do-not-trade prevents recommendations, penalties, and caps.
- **FAILED** outcomes: technical errors stop further processing and emit FailedRunPacket only.
- **Partial portfolio completion**: portfolio may be COMPLETED with some VETOED/FAILED holdings if threshold not exceeded; otherwise VETOED.

### 5.2 What Must NOT Be Tested
- Free-form narrative content (notes, limitations, disclaimers) beyond schema presence.
- Subjective narrative phrasing or tone.

Governance decisions must always be logged and deterministic. Tests must validate emitted outcomes and the presence of required audit artifacts, not narrative text content.

---

## 6. Canonicalization & Hash Validation
Mandatory tests must assert that:

- **Identical logical inputs produce identical hashes**, regardless of ordering or runtime metadata.
- **Ordering variance does not affect hashes** (holdings, penalties, agent outputs).
- **Non-decision fields do not affect hashes**, including run IDs, runtime timestamps, and narrative-only text.
- **Hashes are stable across environments**, with the same canonicalization rules and serialization format.

Any canonicalization failure is **blocking** and must stop the run.

---

## 7. CI/CD & Deployment Alignment
Testing gates deployment; **deployment cannot bypass failing tests**. The required status per promotion stage is:

### 7.1 DEV → STAGING
**Required to pass (blocking):**
- Unit Tests
- Contract Tests
- Deterministic Replay Tests
- Governance Enforcement Tests
- Canonicalization/Hash Tests
- Portfolio Outcome Tests

**May pass with warnings (non-blocking):**
- Documentation-only checks (no decision-significant impact)

### 7.2 STAGING → PROD
**Required to pass (blocking):**
- All tests required for DEV → STAGING
- Regression & Non-Regression Tests (baseline hashes)
- Fixture Compliance Tests

**No non-blocking failures allowed** for production promotion.

---

## 8. Traceability Matrix

| DD Document | Test Type | Fixture | Blocking Rule |
| --- | --- | --- | --- |
| DD-01 Schema Specifications | Schema Validation Unit Tests | TF-01, TF-02, TF-04 | Blocking for any schema violation |
| DD-02 Data Contracts | Contract Tests / Provenance Guards | TF-01, TF-11 | Blocking for missing SourceRef or contract violation |
| DD-03 Agent Interface Contracts | Agent Envelope Contract Tests | TF-01, TF-04 | Blocking for envelope or status/ confidence errors |
| DD-04 Orchestration Flow & State Machine | Deterministic Replay + Outcome Tests | TF-01, TF-04, TF-14 | Blocking for incorrect outcomes or ordering |
| DD-05 Penalty Engine Spec | Penalty Unit + Portfolio Outcome Tests | TF-05, TF-06, TF-08, TF-10, TF-12 | Blocking for penalty logic or cap mismatches |
| DD-06 Governance Rules | Governance Enforcement + Precedence Tests | TF-02, TF-03, TF-05 | Blocking for precedence violations |
| DD-07 Canonicalization Spec | Canonicalization/Hash Tests | TF-12, TF-13 | Blocking for hash instability |
| DD-08 Orchestration Guards | Guard Enforcement + Failure Classification Tests | TF-02, TF-03, TF-04, TF-09, TF-14 | Blocking for guard breaches |
| DD-09 Test Fixture Specifications | Fixture Compliance + Replay Tests | TF-01 through TF-14 | Blocking for fixture non-compliance |

---

## 9. Acceptance Criteria
The test strategy is complete if:
- Every DD (DD-01 through DD-09) is covered by at least one test type.
- Determinism is enforceable via tests (ordering + canonical hash stability).
- Governance outcomes are testable with precedence preserved.
- Deployment cannot bypass failing tests at any promotion stage.

---

## 10. Output Rules
- This document is the single authoritative test strategy for DD-10.
- No placeholders and no new architecture were introduced.
- Any ambiguity was resolved conservatively with explicit constraints.
