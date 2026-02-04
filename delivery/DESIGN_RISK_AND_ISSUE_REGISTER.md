# Design Risk and Issue Register

## 1. Purpose
This document represents a **post-remediation design assurance review** of the Detailed Design artefacts. It provides a clean, current snapshot of residual design risks and design issues based solely on the present DD documentation set.

## 2. Design Risk Register

### R-01
**Risk ID:** R-01  
**Description:** The orchestration flow references PSCC “pre-checks,” yet the phase outputs do not explicitly include PSCC output production, leaving execution timing and dependency ordering ambiguous for portfolio-level concentration checks.  
**Affected DD file(s):** DD-04_ORCHESTRATION_FLOW.md; DD-04_ORCHESTRATION_STATE_MACHINE.md; DD-03_AGENT_INTERFACE_CONTRACTS.md; DD-02_DATA_CONTRACTS.md  
**Likelihood:** Medium  
**Impact:** Medium  
**Risk Rating:** Medium, because ambiguity in PSCC execution timing can cause inconsistent portfolio-level enforcement in implementation.  
**Mitigation Strategy:** Clarify in DD-04 the explicit phase and output ownership for PSCC (input prerequisites, output emission timing, and gating relationship to aggregation).  
**Status:** OPEN  
**Residual Risk Commentary:** Until PSCC timing is explicitly anchored, orchestration correctness remains susceptible to divergent implementations.

### R-02
**Risk ID:** R-02  
**Description:** Provenance requirements are specified both as MetricValue.SourceRef (DD-01/DD-02) and as AgentResult-level `source_refs` (DD-03), which risks inconsistent provenance enforcement across guards and agents.  
**Affected DD file(s):** DD-01_SCHEMA_SPECIFICATIONS.md; DD-02_DATA_CONTRACTS.md; DD-03_AGENT_INTERFACE_CONTRACTS.md; DD-08_ORCHESTRATION_GUARDS.md  
**Likelihood:** Medium  
**Impact:** High  
**Risk Rating:** High, because provenance is a core governance control and any ambiguity may permit unsourced numeric values to pass guard checks.  
**Mitigation Strategy:** Consolidate provenance requirements by specifying a single authoritative provenance structure (preferably MetricValue.SourceRef) and explicitly mapping or deprecating any secondary `source_refs` wrapper in DD-03.  
**Status:** OPEN  
**Residual Risk Commentary:** Until provenance ownership is unified, guard enforcement risks inconsistent interpretation across components.

### R-03
**Risk ID:** R-03  
**Description:** Canonicalization is defined as mandatory for decision-significant outputs, while guard rules restrict canonical output hashing to COMPLETED runs; the interplay for non-completed outcomes is not explicitly reconciled, which may lead to inconsistent hashing expectations.  
**Affected DD file(s):** DD-07_CANONICALIZATION_SPEC.md; DD-08_ORCHESTRATION_GUARDS.md; DD-04_ORCHESTRATION_FLOW.md  
**Likelihood:** Low  
**Impact:** Medium  
**Risk Rating:** Low to Medium, because ambiguity may surface during audit or replay validation for VETOED/FAILED outcomes.  
**Mitigation Strategy:** Add an explicit statement in DD-07 or DD-08 clarifying canonicalization expectations for non-COMPLETED outcomes (e.g., whether canonical payloads are constructed but hashes are withheld).  
**Status:** OPEN  
**Residual Risk Commentary:** Without explicit guidance, replay tooling may diverge on handling of non-completed runs.

### R-04
**Risk ID:** R-04  
**Description:** Partial portfolio failure thresholds are defined as a RunConfig field in guards and fixtures, but the state machine does not explicitly indicate where threshold evaluation occurs in the transition sequence.  
**Affected DD file(s):** DD-08_ORCHESTRATION_GUARDS.md; DD-09_TEST_FIXTURE_SPECIFICATIONS.md; DD-04_ORCHESTRATION_STATE_MACHINE.md  
**Likelihood:** Medium  
**Impact:** Medium  
**Risk Rating:** Medium, as transition ambiguity can cause divergent interpretations of when VETOED outcomes are applied at portfolio scope.  
**Mitigation Strategy:** Annotate the portfolio-level state transition where partial failure threshold evaluation is applied and how it interacts with aggregation readiness.  
**Status:** OPEN  
**Residual Risk Commentary:** The threshold logic is defined but not fully anchored to a specific state transition.

### R-05
**Risk ID:** R-05  
**Description:** Test fixtures introduce a `debug_mode` field in RunConfig without an explicit schema definition in the data contracts, risking non-deterministic test interpretation and mismatched implementation expectations.  
**Affected DD file(s):** DD-09_TEST_FIXTURE_SPECIFICATIONS.md; DD-02_DATA_CONTRACTS.md  
**Likelihood:** Medium  
**Impact:** Medium  
**Risk Rating:** Medium, because fixture-driven tests may diverge from authoritative contracts.  
**Mitigation Strategy:** Either define `debug_mode` explicitly in RunConfig contracts or remove it from fixture requirements if it is not a supported design field.  
**Status:** OPEN  
**Residual Risk Commentary:** Until aligned, testability and contract conformance remain at risk.

## 3. Design Issue Log

### I-01
**Issue ID:** I-01  
**Description:** `RunConfig.debug_mode` is referenced in the test fixture specification but is not defined in the data contracts or schema specifications.  
**Affected DD file(s):** DD-09_TEST_FIXTURE_SPECIFICATIONS.md; DD-02_DATA_CONTRACTS.md  
**Severity:** Medium  
**Root Cause:** Fixture specification not aligned to RunConfig contract definition.  
**Resolution Status:** OPEN  
**Notes:** The fixture expectations cannot be validated against the current contract scope until the field is either defined or removed.

### I-02
**Issue ID:** I-02  
**Description:** PSCC output production timing is not explicitly defined in the orchestration flow phases, despite being referenced as a portfolio-level output in later aggregation steps.  
**Affected DD file(s):** DD-04_ORCHESTRATION_FLOW.md; DD-04_ORCHESTRATION_STATE_MACHINE.md  
**Severity:** Medium  
**Root Cause:** Orchestration phase outputs do not enumerate PSCC output production, creating a sequencing gap.  
**Resolution Status:** OPEN  
**Notes:** Without explicit timing, orchestration implementations may schedule PSCC inconsistently.

## 4. Accepted Risks
No risks are explicitly accepted in this review. All listed risks remain OPEN pending design clarification.

## 5. Assurance Summary
**Overall design risk posture:** Medium.  
**Confidence level in proceeding to implementation:** Moderate, contingent on resolving the identified orchestration and contract ambiguities.  
**Key strengths after remediation:** The DD set is internally consistent on governance precedence, determinism mandates, and portfolio-first orchestration principles.  
**Remaining concerns:** Provenance ownership, PSCC sequencing, and fixture/contract alignment require clarification to avoid inconsistent implementations.  
**Explicit assumptions:** This review assumes HLD v1.0 remains authoritative and that no external schema extensions exist beyond the DD artefacts reviewed.
