# DD-12 — Deployment Risk Register (Authoritative, Production-Grade)

## 1. Scope & Constraints
This register covers **deployment-phase risks only**, aligned to DD-11 Phased Deployment Plan and DD-01 through DD-10. It enforces deterministic execution, governance precedence, portfolio-first safety, canonicalization & replayability, and test-gated promotion. No new architecture or features are introduced.

**Deployment Phases (DD-11):** Phase 0 (Pre-Deployment Readiness) through Phase 5 (Post-Deployment Validation & Monitoring).

## 2. Rating Method
**Likelihood** and **Impact** are rated **Low / Medium / High**. **Risk Rating** is derived from the matrix below:

| Likelihood \ Impact | Low | Medium | High |
| --- | --- | --- | --- |
| Low | Low | Low | Medium |
| Medium | Low | Medium | High |
| High | Medium | High | High |

## 3. Deployment Risk Register

### DR-01 — Configuration Drift Across Environments
- **Risk Description:** Release configuration diverges across environments (RunConfig, ConfigSnapshot, registries, rubric versions), breaking deterministic behavior and governance enforcement during promotion.
- **Affected Deployment Phase(s):** 0–5
- **Likelihood:** Medium
- **Impact:** High
- **Risk Rating:** High
- **Detection Method:** Hash comparison against release manifest at each phase; RunLog records config_hash and snapshot_hash for audit.
- **Mitigation Strategy:** Version-pinned configuration bundle promotion only; immutability checks and blocking drift detection per DD-11.
- **Contingency / Rollback Action:** Revert to last-known-good ConfigSnapshot bundle and registry manifest; re-run deterministic fixtures before resuming promotion.
- **Residual Risk:** Low
- **Risk Owner:** Deployment Lead

### DR-02 — RunConfig / ConfigSnapshot / Registry Hash Mismatch
- **Risk Description:** Environment-specific hash mismatch for RunConfig/ConfigSnapshot/registries causes orchestration refusal or inconsistent decisions across environments.
- **Affected Deployment Phase(s):** 0–4
- **Likelihood:** Medium
- **Impact:** High
- **Risk Rating:** High
- **Detection Method:** Manifest hash validation and RunLog hash audit; deterministic replay tests and canonicalization/hash tests.
- **Mitigation Strategy:** Hash validation enforced as blocking gate; orchestrator refuses to run when hashes do not match release manifest.
- **Contingency / Rollback Action:** Halt promotion; revert to last-known-good manifest; repeat validation checks before re-attempting.
- **Residual Risk:** Low
- **Risk Owner:** Platform Lead

### DR-03 — Governance Precedence Regression After Deployment
- **Risk Description:** Governance enforcement order deviates from authoritative precedence (DIO → GRRA → Risk Officer → LEFO → PSCC → penalties → Chair), resulting in invalid outcomes.
- **Affected Deployment Phase(s):** 1–5
- **Likelihood:** Medium
- **Impact:** High
- **Risk Rating:** High
- **Detection Method:** Governance enforcement tests; RunLog governance decision trail verification; guard G6 enforcement checks.
- **Mitigation Strategy:** Mandatory governance enforcement tests as blocking gates; guard enforcement in orchestration to prevent bypass.
- **Contingency / Rollback Action:** Immediate rollback to last-known-good governance package; flag all runs in regression window for replay validation and audit review.
- **Residual Risk:** Medium
- **Risk Owner:** Governance Owner

### DR-04 — Canonicalization & Hash Drift Across Environments
- **Risk Description:** Non-deterministic ordering or serialization differences cause canonical hash drift between environments, undermining replayability and auditability.
- **Affected Deployment Phase(s):** 1–5
- **Likelihood:** Medium
- **Impact:** High
- **Risk Rating:** High
- **Detection Method:** Deterministic replay tests; canonicalization/hash tests; cross-environment hash comparisons for fixtures.
- **Mitigation Strategy:** Enforce DD-07 canonical ordering and serialization rules; guard G7 determinism checks; block promotion on any hash variance.
- **Contingency / Rollback Action:** Roll back to last stable canonicalization rules and hash baselines; re-run fixture replays before resuming.
- **Residual Risk:** Low
- **Risk Owner:** Platform Lead

### DR-05 — Test Gate Bypass During Promotion
- **Risk Description:** Promotion proceeds without required DD-10 test gates passing, allowing regressions into higher environments or production.
- **Affected Deployment Phase(s):** 0–4
- **Likelihood:** Low
- **Impact:** High
- **Risk Rating:** Medium
- **Detection Method:** CI/CD promotion audit trail; verification that required test artifacts exist for the phase.
- **Mitigation Strategy:** Enforce test gates as blocking at each phase; production promotion requires zero warnings per DD-11/DD-10.
- **Contingency / Rollback Action:** Stop rollout and revert to last-known-good release; re-run required test suites before re-attempting.
- **Residual Risk:** Low
- **Risk Owner:** Deployment Lead

### DR-06 — Partial Portfolio Threshold Misapplication
- **Risk Description:** Partial failure threshold (run_config.partial_failure_veto_threshold_pct) miscomputed or applied at the wrong time, leading to incorrect portfolio_run_outcome during rollout.
- **Affected Deployment Phase(s):** 2–5
- **Likelihood:** Medium
- **Impact:** Medium
- **Risk Rating:** Medium
- **Detection Method:** Portfolio outcome tests; RunLog audit of failure_rate_pct computation and threshold comparison; guard G9 validation.
- **Mitigation Strategy:** Enforce DD-04/DD-08 timing and formula; block on any outcome discrepancy in tests.
- **Contingency / Rollback Action:** Roll back orchestrator version to last-known-good; re-run deterministic fixtures for validation.
- **Residual Risk:** Low
- **Risk Owner:** Orchestration Lead

### DR-07 — Agent Conformance Failures in Production
- **Risk Description:** Agents emit non-conformant AgentResult envelopes or invalid field values, causing invalid outputs or improper run classifications after deployment.
- **Affected Deployment Phase(s):** 1–5
- **Likelihood:** Medium
- **Impact:** Medium
- **Risk Rating:** Medium
- **Detection Method:** Agent envelope contract tests; guard G5 conformance checks; RunLog error records for conformance violations.
- **Mitigation Strategy:** Enforce AgentResult schema contracts as blocking gates; fail holding or stop run deterministically per DD-08.
- **Contingency / Rollback Action:** Roll back agent release to last-known-good version; re-run contract tests before resuming promotion.
- **Residual Risk:** Low
- **Risk Owner:** Agent Lead

### DR-08 — Penalty Engine Mis-sequencing
- **Risk Description:** Penalties are applied to vetoed or short-circuited holdings, or applied before LEFO/PSCC caps, violating governance precedence.
- **Affected Deployment Phase(s):** 2–5
- **Likelihood:** Medium
- **Impact:** High
- **Risk Rating:** High
- **Detection Method:** Governance enforcement tests; penalty computation tests; RunLog governance trail showing penalty application order.
- **Mitigation Strategy:** Enforce DD-05 precedence invariants and DD-06 governance order via guard G6; block any sequencing violations.
- **Contingency / Rollback Action:** Roll back governance/penalty engine package; re-run fixtures and governance tests before resuming.
- **Residual Risk:** Medium
- **Risk Owner:** Governance Owner

### DR-09 — Observability & Audit Gaps Post-Deployment
- **Risk Description:** Missing RunLogs, hashes, or guard records prevent audit and replay verification after deployment.
- **Affected Deployment Phase(s):** 3–5
- **Likelihood:** Medium
- **Impact:** High
- **Risk Rating:** High
- **Detection Method:** Audit checks for RunLog presence, decision hashes, guard counters, and replay artifacts; monitoring for missing artifacts.
- **Mitigation Strategy:** Enforce required logging and artifact emission per DD-11; emission guards block outputs when required artifacts are missing.
- **Contingency / Rollback Action:** Halt rollout and revert to last-known-good release; re-run deterministic fixtures to re-establish baselines and logs.
- **Residual Risk:** Medium
- **Risk Owner:** Platform Lead

### DR-10 — Rollback Integrity Failure
- **Risk Description:** Rollback breaks determinism or audit continuity (e.g., mismatched manifests or missing replay baselines), invalidating audit trails.
- **Affected Deployment Phase(s):** 4–5
- **Likelihood:** Low
- **Impact:** High
- **Risk Rating:** Medium
- **Detection Method:** Post-rollback deterministic replay checks; hash validation against last-known-good baselines; RunLog audit for continuity.
- **Mitigation Strategy:** Deterministic rollback to last-known-good manifest only; mandatory fixture replay after rollback before resuming service.
- **Contingency / Rollback Action:** Freeze promotion; re-apply last-known-good ConfigSnapshot bundle and re-validate hashes and fixtures.
- **Residual Risk:** Low
- **Risk Owner:** Deployment Lead

### DR-11 — Environment Parity Risk (Locale/Time/Serialization)
- **Risk Description:** Environment differences (locale, time settings, numeric serialization) produce replay mismatches or hash drift across environments.
- **Affected Deployment Phase(s):** 1–5
- **Likelihood:** Medium
- **Impact:** High
- **Risk Rating:** High
- **Detection Method:** Cross-environment deterministic replay tests; hash comparison of identical fixtures across phases.
- **Mitigation Strategy:** Enforce DD-07 canonicalization rules and deterministic serialization; fixed UTC timestamps for fixtures; block promotions on mismatch.
- **Contingency / Rollback Action:** Halt promotion and revert to last-known-good environment configuration; re-run fixture replay tests before re-attempt.
- **Residual Risk:** Medium
- **Risk Owner:** Platform Lead

### DR-12 — Deployment Sequencing Order Violation
- **Risk Description:** Component deployment order deviates from the mandatory sequence (schemas → registries → canonicalization → guards → governance → penalties → agents → aggregation), causing invalid enforcement or missing dependencies.
- **Affected Deployment Phase(s):** 0–4
- **Likelihood:** Low
- **Impact:** Medium
- **Risk Rating:** Low
- **Detection Method:** Deployment checklist validation against DD-11 component order; promotion manifest review.
- **Mitigation Strategy:** Enforce required deployment order as a gating checklist item; block promotion if order is violated.
- **Contingency / Rollback Action:** Stop rollout, restore last-known-good deployment state, then redeploy in authoritative sequence.
- **Residual Risk:** Low
- **Risk Owner:** Deployment Lead

## 4. Deployment Risk Matrix (Executive Summary)

| Risk ID | Likelihood | Impact | Rating | Phase(s) |
| --- | --- | --- | --- | --- |
| DR-01 | Medium | High | High | 0–5 |
| DR-02 | Medium | High | High | 0–4 |
| DR-03 | Medium | High | High | 1–5 |
| DR-04 | Medium | High | High | 1–5 |
| DR-05 | Low | High | Medium | 0–4 |
| DR-06 | Medium | Medium | Medium | 2–5 |
| DR-07 | Medium | Medium | Medium | 1–5 |
| DR-08 | Medium | High | High | 2–5 |
| DR-09 | Medium | High | High | 3–5 |
| DR-10 | Low | High | Medium | 4–5 |
| DR-11 | Medium | High | High | 1–5 |
| DR-12 | Low | Medium | Low | 0–4 |

## 5. Completion Check
- All phases (0–5) are covered by at least one deployment risk.
- All **High** and **Medium** risks include explicit mitigation and rollback actions.
- The register supports go/no-go decisions for each promotion phase.
