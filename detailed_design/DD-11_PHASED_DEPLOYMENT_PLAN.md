# DD-11 — Phased Deployment Plan (Portfolio-First, Deterministic, Governance-Safe)

## 1. PURPOSE & DEPLOYMENT PRINCIPLES
This deployment plan defines **authoritative, gated promotion** for the Agentic Investment System, aligned to **HLD v1.0** and **DD-01 through DD-10**. The plan is written for production sign-off and enforces deterministic, replayable execution across environments.

**Objectives**
- Deploy only when **governance and test constraints** are satisfied, as required by DD-10. 
- **No environment promotion without test gate clearance**; failing tests always block promotion. 
- **Determinism and replayability** are mandatory at every stage (canonicalization, ordering, and hashing). 
- **Portfolio-level safety beats speed**; governance precedence is enforced before any scoring, penalties, or output emission. 

**Non-negotiable Principles (from HLD/DDs)**
- Governance precedence: **DIO VETO → GRRA SHORT_CIRCUIT → Risk Officer VETO → LEFO caps → PSCC caps → Penalties → Chair aggregation**. 
- Deterministic ordering and canonicalization are required for reproducibility. 
- No invented numbers; provenance required for numeric metrics. 
- Portfolio-first orchestration and partial portfolio rules are enforced.

---

## 2. DEPLOYMENT PHASE MODEL (AUTHORITATIVE)

### Phase 0: Pre-Deployment Readiness
**Purpose**
- Establish configuration integrity, registry completeness, and deterministic readiness **before any runtime execution**.

**Entry criteria**
- All configuration artifacts (RunConfig, ConfigSnapshot, registries, rubric versions) are versioned and frozen for the release.
- Baseline fixtures from DD-09 are available for deterministic replay.

**Exit criteria**
- Version pinning and configuration immutability checks pass.
- Pre-flight validation confirms no config drift vs. release baseline.

**Blocking conditions**
- Missing or mismatched ConfigSnapshot/registry versions.
- Any failure in configuration validation or version pinning.

**Artifacts produced**
- Release ConfigSnapshot (versioned)
- Registry version manifest
- Release checklist with pinned fixture version IDs

**Test gates required (DD-10)**
- Contract tests for configuration schemas (blocking). 
- Fixture compliance checks (blocking).

---

### Phase 1: Local / Developer Validation
**Purpose**
- Validate deterministic behavior and schema/contract correctness on developer environments.

**Entry criteria**
- Phase 0 artifacts available and version-pinned.
- Local environment has the release configuration manifest.

**Exit criteria**
- All required unit, contract, and determinism tests pass.

**Blocking conditions**
- Any unit or contract test failure.
- Any deterministic replay or canonicalization failure.

**Artifacts produced**
- Local test reports
- Deterministic replay logs
- Canonical hash baselines (local verification only)

**Test gates required (DD-10)**
- Unit Tests (blocking)
- Contract Tests (blocking)
- Deterministic Replay Tests (blocking)
- Governance Enforcement Tests (blocking)
- Canonicalization/Hash Tests (blocking)
- Portfolio Outcome Tests (blocking)

---

### Phase 2: Integration Environment
**Purpose**
- Validate integration of orchestrator, guards, governance, and agents using deterministic fixtures.

**Entry criteria**
- Phase 1 complete with passing test reports.
- Release ConfigSnapshot and registry manifest deployed to integration.

**Exit criteria**
- End-to-end deterministic runs pass with stable hashes.
- Governance outcomes match DD-06 and DD-08 guard precedence.

**Blocking conditions**
- Any governance precedence violation.
- Any mismatch in canonical hashes across repeated runs.

**Artifacts produced**
- Integration run logs with deterministic hashes
- Governance decision audit trail
- Fixture replay results

**Test gates required (DD-10)**
- Unit Tests (blocking)
- Contract Tests (blocking)
- Deterministic Replay Tests (blocking)
- Governance Enforcement Tests (blocking)
- Canonicalization/Hash Tests (blocking)
- Portfolio Outcome Tests (blocking)

---

### Phase 3: Staging (Pre-Production)
**Purpose**
- Validate release behavior in a production-like environment with full governance and auditability.

**Entry criteria**
- Phase 2 complete with passing test reports.
- Staging is configured with the exact release ConfigSnapshot and registries.

**Exit criteria**
- Staging baselines match expected outputs and hashes.
- Regression suite passes with no decision-significant drift.

**Blocking conditions**
- Any regression in decision-significant outputs.
- Any failure in fixture compliance or deterministic replay.

**Artifacts produced**
- Staging regression reports
- Baseline hashes (expected vs actual)
- Release candidate audit log

**Test gates required (DD-10)**
- All Phase 2 gates (blocking)
- Regression & Non-Regression Tests (blocking)
- Fixture Compliance Tests (blocking)

---

### Phase 4: Production Rollout
**Purpose**
- Perform controlled production deployment with immutable configuration and deterministic guarantees.

**Entry criteria**
- Phase 3 complete with no blocking failures.
- Release artifacts are signed off and immutable.

**Exit criteria**
- Production deployment completed with validated configuration and hash baselines.

**Blocking conditions**
- Any governance or determinism regression detected during rollout.
- Any mismatched configuration hash vs release manifest.

**Artifacts produced**
- Production deployment log
- Deployment manifest with hashes
- RunLog samples for audit

**Test gates required (DD-10)**
- All Phase 3 gates (blocking)
- No non-blocking exceptions; production requires **zero warnings**.

---

### Phase 5: Post-Deployment Validation & Monitoring
**Purpose**
- Confirm production stability, deterministic replayability, and governance enforcement.

**Entry criteria**
- Phase 4 completed; production environment operational.

**Exit criteria**
- Post-deployment replay checks validate canonical hash stability.
- Monitoring shows no determinism drift or governance violations.

**Blocking conditions**
- Any governance violation or determinism drift.
- Any mismatch in replayed hashes vs release baselines.

**Artifacts produced**
- Post-deployment replay reports
- Determinism drift metrics
- Governance audit summaries

**Test gates required (DD-10)**
- Deterministic Replay Tests (blocking)
- Canonicalization/Hash Tests (blocking)
- Governance Enforcement Tests (blocking)
- Regression & Non-Regression checks (blocking)

---

## 3. COMPONENT DEPLOYMENT ORDER
**Required order (authoritative):**
1. **Schema and contracts** (DD-01, DD-02, DD-03)  
2. **Registries and configuration snapshots** (ConfigSnapshot, HardStopFieldRegistry, PenaltyCriticalFieldRegistry)  
3. **Canonicalization logic and hash rules** (DD-07)  
4. **Orchestration guards** (DD-08)  
5. **Governance enforcement layer** (DD-06)  
6. **Penalty engine** (DD-05)  
7. **Agent execution** (DD-03 contracts)  
8. **Aggregation and output emission** (DD-04 orchestration flow/state machine)

**Why this order is mandatory**
- **Schemas and contracts** must exist before any runtime component can validate inputs or outputs. 
- **Registries/ConfigSnapshot** are required by DIO and penalty logic; without them, governance and penalty behavior cannot be deterministic. 
- **Canonicalization rules** must be in place before any output is emitted to guarantee replayability. 
- **Guards** enforce schema, provenance, and deterministic ordering before governance and penalties execute. 
- **Governance** depends on guard outcomes and must be enforced prior to any penalty or aggregation. 
- **Penalty engine** applies only after governance precedence allows it. 
- **Agent execution** produces signals that are validated and governed; it cannot precede schema, guard, and governance layers. 
- **Aggregation/output emission** must occur last to preserve deterministic, governed outcomes.

---

## 4. TEST & GOVERNANCE GATES
**Mandatory rule:** Governance violations **always block promotion**.

For each phase, the following test categories are required (DD-10):

### Phase 0
- Required: Contract Tests (configuration schemas), Fixture Compliance Tests. 
- Blocking failures: any schema/config mismatch or fixture non-compliance. 
- Warnings allowed: none (pre-deployment readiness is strict).

### Phase 1
- Required: Unit, Contract, Deterministic Replay, Governance Enforcement, Canonicalization/Hash, Portfolio Outcome Tests. 
- Blocking failures: any test failure or governance precedence violation. 
- Warnings allowed: documentation-only checks (non-decision-significant) only.

### Phase 2
- Required: same as Phase 1. 
- Blocking failures: any mismatch in deterministic replay or governance outcomes. 
- Warnings allowed: documentation-only checks only.

### Phase 3
- Required: all Phase 2 gates plus Regression & Non-Regression Tests and Fixture Compliance Tests. 
- Blocking failures: any decision-significant regression or fixture mismatch. 
- Warnings allowed: none (pre-production is strict).

### Phase 4
- Required: all Phase 3 gates; production allows **no warnings**. 
- Blocking failures: any governance or determinism violation, config hash mismatch, or regression. 
- Warnings allowed: none.

### Phase 5
- Required: Deterministic Replay, Canonicalization/Hash, Governance Enforcement, Regression checks. 
- Blocking failures: any determinism drift, governance violation, or regression. 
- Warnings allowed: none (post-deployment validation is a hard gate for continued operation).

---

## 5. CONFIGURATION & VERSIONING STRATEGY
**Promotion rules**
- **RunConfig, ConfigSnapshot, registries, and rubric versions** are promoted together as a **single, version-pinned bundle**. 
- Each environment uses the exact same version identifiers; no environment-local edits.

**Drift prevention**
- ConfigSnapshot and registry hashes are compared against release manifests at every phase. 
- Any hash mismatch is a **blocking failure** and halts promotion.

**Rollback handling**
- If configuration validation fails, rollback reverts to the last known-good ConfigSnapshot bundle and registry manifest. 
- Rollback does not alter historical run outputs; it only re-pins configuration for future runs.

**Version pinning enforcement**
- Orchestrator must refuse to run if environment configuration hashes do not match the release manifest. 
- RunLog records the config version and hashes for auditability.

---

## 6. ROLLBACK & FAILURE HANDLING
Rollback must be **deterministic** and preserve auditability; historical results are immutable.

**Failed deployments**
- Revert to last-known-good release manifest (ConfigSnapshot + registries + rubric versions). 
- Re-run deterministic fixtures in the target environment before resuming service.

**Governance regressions**
- Immediate rollback to last-known-good governance configuration and guard enforcement package. 
- All runs during the regression window are flagged for replay validation and audit review.

**Canonicalization / hash instability**
- Treat as a critical failure; stop promotion or rollback to prior canonicalization rules and hash baselines. 
- Update fixture baselines only via explicit version increment and governance review (per DD-09/DD-10).

**Partial portfolio failures in PROD**
- Enforce DD-04/DD-08 partial failure threshold deterministically. 
- If threshold exceeded, mark portfolio_run_outcome=VETOED and prevent aggregation output; do not mutate past results.

---

## 7. OBSERVABILITY & POST-DEPLOYMENT CONTROLS
**Required logs and metrics per environment**
- RunLog with outcome classification and governance decision trail. 
- Canonical hashes for inputs and decision outputs (when allowed by DD-07). 
- Guard violation counters per guard (G0–G10). 

**Governance enforcement monitoring**
- Track counts of VETOED, SHORT_CIRCUITED, FAILED, and COMPLETED outcomes. 
- Alert on unexpected changes in veto rates or precedence violations.

**Determinism drift detection**
- Periodic replay of fixed DD-09 fixtures; hashes must match baselines. 
- Alert on any hash mismatch or ordering variance.

**Replay validation checks post-deployment**
- Recompute snapshot_hash, config_hash, run_config_hash, and decision_hash for sampled runs. 
- Validate that emitted hashes match canonical recomputation.

---

## 8. DEPLOYMENT RISKS & CONTROLS
**Risk: Configuration drift across environments**  
Control: Version pinning, hash validation, and release manifest enforcement; failures block promotion.

**Risk: Governance precedence regression**  
Control: Governance Enforcement Tests + guard precedence checks (DD-10); blocking at all phases.

**Risk: Canonicalization/hash instability**  
Control: Deterministic Replay + Canonicalization/Hash Tests; blocking and rollback to last stable baselines.

**Risk: Unsourced or inconsistent data**  
Control: Provenance Guards (G2) and Contract Tests; any violation blocks promotion.

**Risk: Partial portfolio instability**  
Control: Partial portfolio guards (G9) and Portfolio Outcome Tests; enforced per DD-04/DD-08.

**Risk: Agent output non-conformance**  
Control: Agent Output Conformance Guards (G5) and Contract Tests; failures block promotion.

---

## 9. ACCEPTANCE CRITERIA
This deployment plan is complete if:
- All phases are defined, gated, and aligned to DD-10 test requirements. 
- Test strategy is enforced as mandatory gates (not advisory). 
- Rollback procedures are deterministic and preserve auditability. 
- Governance cannot be bypassed at any stage. 
- The system is safe to operate in production with replayable, deterministic outputs.

---

## 10. OUTPUT RULES
- Single markdown file: **DD-11_PHASED_DEPLOYMENT_PLAN.md**
- No placeholders
- Clear, auditable language for production sign-off
- No new architecture introduced; conflicts would be surfaced conservatively (none detected)
