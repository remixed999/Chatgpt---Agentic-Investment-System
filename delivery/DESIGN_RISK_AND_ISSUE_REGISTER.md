# Design Risk and Issue Register

## 1. Purpose
This document provides a formal design assurance review of the Detailed Design phase. It records design risks and design issues observed across the detailed design artefacts and identifies required design actions to preserve determinism, governance precedence, portfolio-first consistency, and auditability.

## 2. Design Risk Register

### R-01
Risk ID: R-01
Description: The orchestration state machine specification is a placeholder, creating a material gap in deterministic transition definitions and terminal outcome handling across portfolio and holding scopes.
Affected DD file(s): DD-04_ORCHESTRATION_STATE_MACHINE.md
Likelihood: High
Impact: High
Risk Rating: High, because the absence of a defined state machine directly undermines deterministic and reproducible orchestration behavior.
Mitigation Strategy: Replace the placeholder with a complete state machine definition aligned to the orchestration flow, including explicit transitions, terminal outcomes, and mapping to output eligibility.
Residual Risk after mitigation: Medium, because alignment across multiple DDs still requires verification.

### R-02
Risk ID: R-02
Description: Governance precedence and outcome eligibility are defined across multiple DD documents without a single consolidated reconciliation point, increasing the risk of inconsistent enforcement across guards, governance rules, and orchestration flow.
Affected DD file(s): DD-04_ORCHESTRATION_FLOW.md, DD-06_GOVERNANCE_RULES.md, DD-08_ORCHESTRATION_GUARDS.md
Likelihood: Medium
Impact: High
Risk Rating: High, due to the criticality of precedence order and the number of documents defining enforcement behavior.
Mitigation Strategy: Introduce a cross-DD precedence reconciliation section that explicitly maps guard actions to governance rules and orchestration terminal outcomes, and require conformance checks in acceptance criteria.
Residual Risk after mitigation: Medium.

### R-03
Risk ID: R-03
Description: Ambiguities in VETOED versus FAILED handling at holding scope may cause inconsistent governance outcomes and undermine reproducibility of per-holding results.
Affected DD file(s): DD-02_DATA_CONTRACTS.md, DD-04_ORCHESTRATION_FLOW.md, DD-08_ORCHESTRATION_GUARDS.md
Likelihood: Medium
Impact: High
Risk Rating: High, because ambiguous outcome classification affects the core governance model and downstream packet eligibility.
Mitigation Strategy: Align contract failure semantics and guard actions to a single authoritative rule set that clearly distinguishes VETOED from FAILED for identity and schema violations.
Residual Risk after mitigation: Low to Medium.

### R-04
Risk ID: R-04
Description: Canonicalization and hashing requirements are specified, but several documents reference inconsistent DD identifiers and versions, creating a risk of non-compliant implementation and audit traceability errors.
Affected DD file(s): DD-07_CANONICALIZATION_SPEC.md, DD-09_TEST_FIXTURE_SPECIFICATIONS.md
Likelihood: Medium
Impact: Medium
Risk Rating: Medium, because inconsistent references can lead to implementation drift and test coverage gaps.
Mitigation Strategy: Normalize DD numbering references and version identifiers across all documents; add explicit reference mapping in DD-09 test fixtures.
Residual Risk after mitigation: Low.

### R-05
Risk ID: R-05
Description: Partial portfolio run thresholds are defined as a fixed percentage without a stable configuration reference, creating uncertainty in governance enforcement and testability across run modes.
Affected DD file(s): DD-08_ORCHESTRATION_GUARDS.md, DD-09_TEST_FIXTURE_SPECIFICATIONS.md
Likelihood: Medium
Impact: Medium
Risk Rating: Medium, because the threshold affects portfolio-level outcomes and determinism across runs.
Mitigation Strategy: Explicitly bind the threshold to a RunConfig field or ConfigSnapshot registry and ensure deterministic default values are recorded.
Residual Risk after mitigation: Low.

### R-06
Risk ID: R-06
Description: Agent execution ordering rules are defined in guards but are not explicitly harmonized with orchestration flow phases, increasing the risk of non-deterministic execution paths.
Affected DD file(s): DD-04_ORCHESTRATION_FLOW.md, DD-08_ORCHESTRATION_GUARDS.md
Likelihood: Medium
Impact: Medium
Risk Rating: Medium, due to potential ordering-induced divergence in outputs.
Mitigation Strategy: Add explicit ordering requirements to the orchestration flow phase definitions and align with canonicalization ordering rules.
Residual Risk after mitigation: Low.

## 3. Design Issue Log

### I-01
Issue ID: I-01
Description: The orchestration state machine document is a placeholder and does not contain the required state machine definition.
Affected DD file(s): DD-04_ORCHESTRATION_STATE_MACHINE.md
Severity: High
Root Cause: Incomplete document content.
Recommended Design Fix: Provide a full state machine specification that maps to the orchestration flow phases and outcome eligibility matrix.
Requires DD Change: Yes

### I-02
Issue ID: I-02
Description: Holding identity missing fields are treated as VETO-eligible in data contracts, but as FAILED in orchestration guards, creating a direct conflict in outcome semantics.
Affected DD file(s): DD-02_DATA_CONTRACTS.md, DD-08_ORCHESTRATION_GUARDS.md
Severity: High
Root Cause: Conflicting outcome classification rules across documents.
Recommended Design Fix: Standardize identity field omissions to a single outcome classification and update guard actions and contract failure semantics accordingly.
Requires DD Change: Yes

### I-03
Issue ID: I-03
Description: Governance rules reference the penalty engine as DD-04, while the penalty specification is DD-05, creating an authoritative reference mismatch.
Affected DD file(s): DD-06_GOVERNANCE_RULES.md, DD-05_PENALTY_ENGINE_SPEC.md
Severity: Medium
Root Cause: Document numbering drift.
Recommended Design Fix: Correct references to the penalty engine specification and verify all cross-DD references.
Requires DD Change: Yes

### I-04
Issue ID: I-04
Description: The canonicalization specification declares versioning as DD-06 v1.0 while the file is DD-07, creating traceability ambiguity.
Affected DD file(s): DD-07_CANONICALIZATION_SPEC.md
Severity: Medium
Root Cause: Inconsistent document version labeling.
Recommended Design Fix: Align the version reference with the correct DD identifier and update downstream references.
Requires DD Change: Yes

### I-05
Issue ID: I-05
Description: The orchestration guards document header states DD-07, conflicting with its file name and with references from other documents.
Affected DD file(s): DD-08_ORCHESTRATION_GUARDS.md
Severity: Medium
Root Cause: Document header not aligned to file identity.
Recommended Design Fix: Update the document header and references to reflect the correct DD number and maintain consistent traceability.
Requires DD Change: Yes

### I-06
Issue ID: I-06
Description: The orchestration flow document status references a transition to DD-04 state and audit, which is inconsistent with the current file naming and sequence.
Affected DD file(s): DD-04_ORCHESTRATION_FLOW.md
Severity: Low
Root Cause: Status metadata not updated after document restructuring.
Recommended Design Fix: Correct the status line to reflect the accurate next-phase document and naming.
Requires DD Change: Yes

### I-07
Issue ID: I-07
Description: Test fixture traceability references incorrect DD identifiers for orchestration flow, penalty engine, canonicalization, and guards, creating a risk of test coverage misalignment.
Affected DD file(s): DD-09_TEST_FIXTURE_SPECIFICATIONS.md
Severity: Medium
Root Cause: Traceability section not synchronized with DD numbering.
Recommended Design Fix: Update traceability references to the correct DD document identifiers to preserve auditability.
Requires DD Change: Yes

## 4. Required Design Actions

1. File name: DD-04_ORCHESTRATION_STATE_MACHINE.md
   Section reference: Entire document
   Summary of required change: Replace placeholder with the complete state machine definition aligned to DD-04 orchestration flow and output eligibility.

2. File name: DD-02_DATA_CONTRACTS.md
   Section reference: Contract Failure Semantics and Holding Input Contract
   Summary of required change: Align identity field omission outcomes with guard definitions to eliminate VETOED versus FAILED conflicts.

3. File name: DD-08_ORCHESTRATION_GUARDS.md
   Section reference: G1 Identity & Portfolio Context Guards
   Summary of required change: Harmonize identity failure outcomes with DD-02 and orchestration flow to ensure consistent governance classification.

4. File name: DD-06_GOVERNANCE_RULES.md
   Section reference: Penalty Governance Integration and precedence references
   Summary of required change: Correct references to the penalty engine specification and ensure the precedence order references the correct DD identifier.

5. File name: DD-07_CANONICALIZATION_SPEC.md
   Section reference: Versioning
   Summary of required change: Correct the DD identifier in the versioning statement and align with current document numbering.

6. File name: DD-08_ORCHESTRATION_GUARDS.md
   Section reference: Document header
   Summary of required change: Update the header to reflect the correct DD identifier for orchestration guards.

7. File name: DD-04_ORCHESTRATION_FLOW.md
   Section reference: Status
   Summary of required change: Correct the status line to reflect accurate document sequencing.

8. File name: DD-09_TEST_FIXTURE_SPECIFICATIONS.md
   Section reference: Traceability references in test matrix
   Summary of required change: Update DD identifiers to reflect the correct sources for orchestration flow, penalty engine, canonicalization, and guards.

9. File name: DD-08_ORCHESTRATION_GUARDS.md
   Section reference: G9 Partial Portfolio Run Guards
   Summary of required change: Bind the 30% threshold to a named RunConfig or registry field and define deterministic defaults.

## 5. Assurance Summary
Overall design risk posture: Medium. The design establishes strong governance and determinism principles, but several documentation inconsistencies and one missing specification materially affect assurance confidence.

Key strengths of the design: The portfolio-first model, explicit governance precedence, and deterministic canonicalization and penalty policies are clearly articulated, which supports auditability and reproducibility when implemented as specified.

Key remaining concerns: The missing state machine, conflicting outcome classifications, and DD reference drift undermine enforceability and test traceability; these must be corrected prior to implementation sign-off.

Assumptions made during assessment: The assessment assumes HLD v1.0 is authoritative, and that all DD documents are intended to be internally consistent and cross-referenced by their file names.
