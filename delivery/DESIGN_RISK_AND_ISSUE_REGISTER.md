# Design Risk and Issue Register

## 1. Purpose
This document represents a **post-remediation design assurance review** of the Detailed Design artefacts. It provides a fresh assessment of residual risks and issues after remediation, without relying on prior risk statuses.

## 2. Design Risk Register

### R-01 — Canonicalization ordering depends on runtime timestamps
- **Description:** The canonicalization rules require veto logs to be ordered by `timestamp`, yet timestamp fields are treated as runtime metadata elsewhere. This can introduce ordering variance across replays when timestamps differ, potentially impacting determinism and reproducibility of canonicalized payloads.
- **Affected DD file(s):** DD-07_CANONICALIZATION_SPEC.md
- **Likelihood:** Medium
- **Impact:** Medium
- **Risk Rating:** Medium. Deterministic outcomes are a core requirement; reliance on runtime timestamps for ordering can cause divergence across environments.
- **Mitigation Strategy:** Define a deterministic ordering key for veto logs that is independent of runtime timestamps, or explicitly exclude veto logs (or their timestamps) from canonicalized payloads and hashes.
- **Status:** OPEN
- **Residual Risk Commentary:** Until ordering is decoupled from runtime timekeeping, replay determinism remains at risk for runs with veto log entries.

### R-02 — Partial failure threshold comparison rule is under-specified
- **Description:** The portfolio-level partial failure threshold is referenced as a percentage but does not define rounding, comparison operators at boundaries, or treatment of unknown outcomes. This leaves room for inconsistent portfolio outcome classification across implementations.
- **Affected DD file(s):** DD-04_ORCHESTRATION_STATE_MACHINE.md; DD-08_ORCHESTRATION_GUARDS.md
- **Likelihood:** Medium
- **Impact:** Medium
- **Risk Rating:** Medium. Outcome classification at thresholds is governance-critical and must be consistent.
- **Mitigation Strategy:** Specify the exact calculation formula (numerator/denominator), rounding policy, and boundary comparison (e.g., `>` vs `>=`) in DD-08 and align DD-04 references accordingly.
- **Status:** OPEN
- **Residual Risk Commentary:** Without explicit threshold math, two compliant implementations could diverge on portfolio VETO outcomes at the same failure ratio.

## 3. Design Issue Log

### I-01 — AgentResult contract fields are inconsistent across DD-02 and DD-03
- **Description:** DD-02 defines AgentResult required fields as `agent_name`, `status`, `confidence`, `key_findings`, `metrics`, `suggested_penalties`, `veto_flags`, while DD-03 defines a different envelope including `agent_version`, `scope`, `outputs`, and `limitations`. The mismatch creates ambiguity for validation and guard enforcement.
- **Affected DD file(s):** DD-02_DATA_CONTRACTS.md; DD-03_AGENT_INTERFACE_CONTRACTS.md
- **Severity:** High
- **Root Cause:** Overlapping schema definitions across DDs without an aligned canonical AgentResult specification.
- **Resolution Status:** OPEN
- **Notes:** A single authoritative AgentResult field list is required to ensure conformance guards are enforceable and deterministic.

### I-02 — HoldingPacket emission rules for FAILED holdings conflict
- **Description:** DD-02 requires a HoldingPacket with identity and outcome for failed holdings, while DD-08 indicates HoldingPackets are omitted when a holding is FAILED. This conflict undermines emission eligibility and testability.
- **Affected DD file(s):** DD-02_DATA_CONTRACTS.md; DD-08_ORCHESTRATION_GUARDS.md; DD-04_ORCHESTRATION_FLOW.md
- **Severity:** High
- **Root Cause:** Divergent interpretations of packet eligibility across governance and contract documents.
- **Resolution Status:** OPEN
- **Notes:** Emission rules must be reconciled to avoid inconsistent output expectations and fixture definitions.

### I-03 — Debug-mode handling of unsourced numbers is inconsistent
- **Description:** DD-05 permits diagnostic continuation in debug mode for unsourced numbers (with penalties and limitations), while DD-08 mandates a DIO veto for any unsourced numeric fact. The inconsistency creates unclear governance outcomes.
- **Affected DD file(s):** DD-05_PENALTY_ENGINE_SPEC.md; DD-08_ORCHESTRATION_GUARDS.md
- **Severity:** Medium
- **Root Cause:** Debug-mode behavior introduced in penalty logic without parallel guard treatment.
- **Resolution Status:** OPEN
- **Notes:** Governance precedence must state whether debug mode can alter enforcement or only logging.

### I-04 — Registry and configuration schemas referenced but not specified
- **Description:** The design references `ConfigSnapshot`, `HardStopFieldRegistry`, and `PenaltyCriticalFieldRegistry`, but these schemas are not defined in DD-01 or DD-02. This prevents deterministic validation and contract enforcement.
- **Affected DD file(s):** DD-05_PENALTY_ENGINE_SPEC.md; DD-02_DATA_CONTRACTS.md
- **Severity:** High
- **Root Cause:** Dependencies on registry/configuration artifacts without corresponding schema specifications.
- **Resolution Status:** OPEN
- **Notes:** Schema definitions or authoritative references must be added to avoid implementation drift.

### I-05 — PortfolioSnapshot fixture definition conflicts with PortfolioConfig contract
- **Description:** DD-09 test fixtures specify `base_currency` within `PortfolioSnapshot`, while DD-02 assigns `base_currency` to `PortfolioConfig` and treats its absence as a portfolio veto condition. This conflict undermines fixture traceability and governance testing.
- **Affected DD file(s):** DD-09_TEST_FIXTURE_SPECIFICATIONS.md; DD-02_DATA_CONTRACTS.md
- **Severity:** Medium
- **Root Cause:** Fixture expectations not aligned to data contract definitions.
- **Resolution Status:** OPEN
- **Notes:** Fixture definitions must conform to the authoritative contract location for `base_currency`.

## 4. Accepted Risks
No risks are formally accepted in this review. Any acceptance requires explicit governance sign-off with documented trade-offs.

## 5. Assurance Summary
- **Overall design risk posture:** Medium.
- **Confidence level in proceeding to implementation:** Moderate, contingent on resolving the identified contract inconsistencies and schema gaps.
- **Key strengths after remediation:** Clear governance precedence, strong determinism requirements, and explicit portfolio-first orchestration flow.
- **Remaining concerns:** Contract misalignments (AgentResult, HoldingPacket emission) and missing registry schemas present a material risk to consistent implementation.
- **Explicit assumptions made during this review:** HLD v1.0 remains authoritative; the DD set under `detailed_design/` is complete and current for this assessment.
