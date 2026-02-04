# TASK 0 — REQUIREMENTS VERIFICATION (UPDATED — PORTFOLIO-FIRST)

## 0.1 Requirements Coverage Matrix

| Requirement ID | Requirement Name                                    | HLD Section(s) Where Addressed                                                                                             |
| -------------- | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| R1             | Scoring Framework Contract                          | §5 (Scorecard, PenaltyBreakdown), §4 (portfolio + per-holding score aggregation)                                           |
| R2             | Evidence & Provenance Contract                      | §5 (SourceRef, MetricValue/MetricWithProvenance), §3 (agent responsibilities), §7 (unsourced number handling)              |
| R3             | Unknown & Staleness Policy                          | §7 (penalty vs veto rules; per-mode thresholds), §5 (missing_reason + not_applicable semantics), §4 (DIO validation gates) |
| R4             | Governance & Veto Matrix                            | §3 (authority + precedence), §4 (portfolio gates + holding gates), §7 (hard-stop criteria)                                 |
| R5             | Standard Agent Output Wrapper                       | §5 (AgentResult schema; required fields; confidence; provenance; veto_flags)                                               |
| R6             | Portfolio Context Model                             | §5 (PortfolioSnapshot, PortfolioConfig, Holdings), §4 (portfolio-first orchestration)                                      |
| R7             | Run Modes (FAST/DEEP)                               | §4 (portfolio FAST vs DEEP flow; per-mode staleness thresholds), §2 (mode boundaries)                                      |
| R8             | Standard Disclosure                                 | §5 (PortfolioCommitteePacket + HoldingPacket disclaimers/limitations), §1 (non-goals)                                      |
| R9             | Currency + Exchange Support                         | §5 (InstrumentIdentity requires ticker+exchange+currency), §4 (identity validation in intake)                              |
| R10            | Portfolio Base Currency Normalization               | §5 (PortfolioConfig.base_currency required), §4 (FX normalization step), §7 (hard-stop if missing)                         |
| R11            | FX Risk Flagging                                    | §3 (Risk Officer + PSCC responsibilities), §5 (fx exposure fields), §7 (FX penalties + flags)                              |
| R12            | Units Consistency                                   | §5 (currency/unit tagging on monetary/ratio fields), §7 (DIO unit validation)                                              |
| R13            | Run Outcome Semantics                               | §4 (orchestration outcomes), §5 (RunLog.portfolio_run_outcome + per_holding_outcomes), §7 (failure taxonomy)               |
| R14            | Registry Split (HardStop vs Penalty-Critical)       | §7 (policy), §5 (ConfigSnapshot registries), §4 (DIO enforcement)                                                          |
| R15            | Burn-Rate Classification Input                      | §4 (RunConfig inputs), §7 (conditional criticality of cash/runway), §5 (RunConfig schema)                                  |
| R16            | Reproducibility Canonicalization                    | §6 (canonicalization rules + hashing), §5 (canonical_output_hash), §4 (deterministic ordering)                             |
| R17            | Corporate Action Risk Category                      | §7 (penalty category policy — Category F: Data Validity), §5 (DIOOutput corporate_action_risk), §8 (tests)                 |
| R18            | Portfolio-Level Operation (multi-holding)           | §2 (system boundaries), §4 (holding loop + portfolio aggregation), §5 (PortfolioCommitteePacket + HoldingPacket schemas)   |
| R19            | Portfolio Concentration/Correlation Controls (PSCC) | §3 (PSCC agent responsibilities), §4 (portfolio aggregation + caps), §7 (override/cap rules)                               |
| R20            | Partial Portfolio Run Policy                        | §4 (portfolio outcome rules), §5 (per_holding_outcomes), §7 (when portfolio run fails vs completes)                        |

---

## 0.2 Clarifications Needed (Portfolio-First)

### C1 — Base Currency Default

* **Question:** What's the default `base_currency` if PortfolioConfig isn't provided?
* **Resolution (recommended):** **No default.**
  * If a **PortfolioSnapshot is provided**, `PortfolioConfig.base_currency` is **required** → if missing: **VETOED** by DIO.
  * If no portfolio is provided (rare / debug-only): report in each instrument's native currency and explicitly flag **"FX aggregation not assessed."**
* **Impact:** Prevents silent FX assumptions and ensures portfolio aggregation is not misleading.

### C2 — Staleness Thresholds (Per Mode, Portfolio-Consistent)

* **Question:** Define precise thresholds per data category and per mode.
* **Recommended defaults:**

**Penalty Thresholds** (triggers penalties, not veto):
  * **Financials:** FAST >120d, DEEP >90d
  * **Price/Volume:** FAST >3 calendar/trading days, DEEP >1 day
  * **Company Updates/Filings/News:** FAST >90d, DEEP >60d
  * **Macro/Regime Inputs:** FAST >14d, DEEP >7d

**Hard-Stop Thresholds** (triggers DIO veto):
  * **Financials:** FAST >365d, DEEP >180d
  * **Price/Volume:** FAST >30d, DEEP >14d
  * **Macro/Regime Inputs:** FAST >90d, DEEP >30d
  * **FX Rates:** FAST >7d, DEEP >48h

* **Impact:** Drives penalties, DIO hard-stop triggers, and the quality label of portfolio outputs.

### C3 — Exchange Field Policy

* **Question:** Enumerate supported exchanges or allow free-form?
* **Recommended default:** `exchange` is **required** and **free-form string** in v0.1, with recommended values list; enum in v1.0.
* **Impact:** Prevents ticker ambiguity; reduces schema brittleness in MVP.

### C4 — LEFO Liquidity Scale

* **Question:** Exact thresholds for 0–5 grade?
* **Recommended default:** Use **dollar ADV** *and* spread if available (more robust across markets), e.g.:
  * 0: effectively untradeable / cannot exit without major slippage
  * 1: exit likely >5 days (even small sizes)
  * 2: 2–5 days
  * 3: <2 days
  * 4: <1 day
  * 5: intraday exit feasible
* **Impact:** Drives hard overrides/caps and portfolio-level liquidity risk aggregation.

### C5 — GRRA Crisis Definition (Cross-Market)

* **Question:** What triggers CRISIS vs RISK_OFF in a portfolio that may include non-US listings?
* **Recommended default:** allow multiple indicator families:
  * Volatility proxy (e.g., VIX if available)
  * Credit stress proxy (if available)
  * Equity drawdown/breadth proxy
  * Funding stress proxy
  * Manual override input for the user (logged with SourceRef)
* **Impact:** Portfolio-wide risk posture and "SHORT_CIRCUITED" decisions.

### C6 — Timezone Standard

* **Question:** How do we store timestamps across exchanges?
* **Recommended default:** store **tz-aware UTC** everywhere, optionally include `original_timezone` as metadata for transparency.
* **Impact:** Prevents freshness calculation bugs and improves reproducibility.

### C7 — Portfolio vs Holding Run Outcomes

* **Question:** If 2 holdings fail, does the whole portfolio run fail?
* **Recommended default:** Portfolio run can still be **COMPLETED** if the orchestrator produced a valid portfolio packet **with explicit per_holding_outcomes**, unless failures exceed a defined threshold (e.g., >30% holdings FAILED/VETOED triggers portfolio-level VETOED or FAILED depending on cause).
* **Impact:** Critical for usability on real portfolios (one bad holding shouldn't nuke the whole run).

---

## 0.3 Missing Areas List (Portfolio-Professional)

These are professional-grade concerns not yet fully defined. They should be explicitly called out as either **MVP in-scope** (as flags) or **v1.0+**.

### M1 — Corporate Actions Handling (splits, consolidations, dividends, spin-offs)

* **Impact:** Historical price/volume and derived metrics can be misleading.
* **Recommendation:** MVP: DIO flags **corporate_action_risk** + penalty category F: Data Validity (see R17). v1.0: adjustment pipeline.

### M2 — Symbol Mapping / Identifier Resolution

* **Impact:** Ticker collisions across exchanges; delistings; renames.
* **Recommendation:** MVP: require `(ticker, exchange)` tuple, optional ISIN. v1.0: ISIN resolution & symbol history.

### M3 — Multi-Asset Instrument Types

* **Impact:** Portfolio may include ETFs, equities, ADRs, options, crypto proxies, etc.
* **Recommendation:** MVP: support common stock + ETFs explicitly; others flagged as "unsupported instrument_type" with conservative penalties/disclosures.

### M4 — Portfolio Concentration & Correlation Estimation Method

* **Impact:** Correlation can be unstable; theme exposure can be subjective.
* **Recommendation:** MVP: rule-based "theme tags" and concentration caps; correlation optional (manual inputs or computed only when adequate price history exists).

### M5 — Compliance / Restrictions Flags

* **Impact:** Real portfolios may include restricted securities / blackout windows.
* **Recommendation:** MVP: informational `compliance_flags` field, no automation. v1.0: configurable restrictions engine.

### M6 — Data Provider Conflict Policy

* **Impact:** different sources disagree; reproducibility breaks if provider changes.
* **Recommendation:** Expand SourceRef to include provider identity/version; DIO contradiction workflow.

### M7 — Batch/Portfolio Scalability & Partial Outcomes

* **Impact:** Many holdings increases failure surface area.
* **Recommendation:** Formalize per-holding subrun outcomes + portfolio-level completion rule (R20).

### M8 — Version Pinning & Replay

* **Impact:** A portfolio packet must be replayable and comparable over time.
* **Recommendation:** Canonicalization rules + hashes (R16) must be explicit and testable.

---

## 0.4 Assumptions (Explicitly Labeled — Updated)

**ASSUMPTION-A1: Portfolio-first run**
* One run ingests **one PortfolioSnapshot** containing **N holdings** (N≥1), plus configuration and seeded/manual data.
* "Single ticker" is represented as a portfolio with N=1 (debug convenience), not the primary model.

**ASSUMPTION-A2: MVP uses manually seeded / user-provided data**
* No live APIs in v0.1; DIO enforces provenance and flags gaps.

**ASSUMPTION-A3: Static agent roster**
* System uses **10 fixed agents** (Chair, DIO, GRRA, Data Ingestion, Fundamentals, Technical, LEFO, PSCC, Risk Officer, Devil's Advocate); no dynamic agent spawning in v0.1.

**ASSUMPTION-A4: Synchronous deterministic orchestration**
* Deterministic ordering of holdings + agents; parallelism optional later but must preserve deterministic merges.

**ASSUMPTION-A5: English-first inputs**
* i18n is out of scope for v0.1.

**ASSUMPTION-A6: Portfolio instrument universe**
* v0.1 focuses on equities/ETFs. Other instruments are either excluded or handled as "informational only" with explicit gaps.

**ASSUMPTION-A7: No real-time streaming**
* Point-in-time snapshots only.

---

## 0.5 Scope Risk List (Portfolio-Relevant)

### RISK-S1: Portfolio Complexity Explosion (HIGH)

* **Issue:** N holdings × many fields × penalties × veto logic can become unmanageable.
* **Mitigation:** Strict schema boundaries, deterministic ordering, and "partial outcomes" policy (R20).
* **Escalation trigger:** If >20% holdings frequently fail due to missing identity/inputs → revise intake UX + validation messaging.

### RISK-S2: FX Normalization Accuracy (HIGH)

* **Issue:** Manual FX rates can be stale/inconsistent; portfolio totals become wrong.
* **Mitigation:** Require timestamps on FX; flag stale FX; optionally allow reporting in native currencies with explicit limitations if FX missing.
* **Escalation trigger:** Repeated >1% reconciliation mismatch in test fixtures.

### RISK-S3: Veto Logic Ambiguity Across Portfolio vs Holding (MEDIUM)

* **Issue:** A holding veto vs portfolio veto confusion.
* **Mitigation:** Explicit precedence + run_outcome semantics per-holding and per-portfolio (R13, R20).
* **Escalation trigger:** Any ambiguous outcome in tests → must be resolved in policy.

### RISK-S4: Correlation/Concentration Misleading Outputs (MEDIUM/HIGH)

* **Issue:** Correlation estimates unstable; "theme tags" subjective.
* **Mitigation:** In MVP, treat correlation as optional; focus on deterministic concentration caps and clear caveats.
* **Escalation trigger:** If correlation logic becomes debate-heavy → keep it advisory and separate from vetoes.

### RISK-S5: LLM Output Drift (Future) (HIGH)

* **Issue:** If LLM agents introduced later, outputs can vary and invent numbers.
* **Mitigation:** DIO post-hoc validation, strict provenance requirement, fail-loud behavior.
* **Escalation trigger:** Any unsourced-number incidents in test runs → tighten schema & validation gates.

### RISK-S6: Unknown vs Not Applicable Confusion (MEDIUM)

* **Issue:** A bank's "burn rate" isn't "unknown", it's "not applicable".
* **Mitigation:** Add explicit semantics:
  * `value=None + missing_reason` = unknown/missing
  * `not_applicable=true` = not relevant for this instrument type/sector
* **Escalation trigger:** If scoring penalizes NA fields incorrectly → revise rubric per sector (v1.0).

### RISK-S7: Regime Whipsaw at Portfolio Level (MEDIUM)

* **Issue:** regime changes too frequently → unstable portfolio posture.
* **Mitigation:** include `regime_confidence`, persistence/hysteresis rules (even if minimal in v0.1).
* **Escalation trigger:** >3 flips per week in test scenarios.

### RISK-S8: Conflicting Overrides (HIGH)

* **Issue:** High score but GRRA crisis + LEFO illiquid + PSCC concentration breach.
* **Mitigation:** Declare strict override hierarchy:
  1. DIO hard-stop (VETOED)
  2. GRRA do_not_trade (SHORT_CIRCUITED)
  3. LEFO illiquidity overrides/caps
  4. PSCC concentration caps
  5. Chair can't override any of the above
* **Escalation trigger:** Any rule conflict in tests → adjust precedence until deterministic.

---

## 0.6 Pre-HLD Decision Summary (Updated)

✅ **Accepted Defaults / Locked Decisions:**

* Portfolio-first: one run evaluates a whole PortfolioSnapshot (N holdings).
* **No default base_currency** when portfolio is provided: it's required or DIO vetoes.
* Timestamps are tz-aware UTC; staleness thresholds per mode (both penalty and hard-stop).
* Exchange is required; free-form string in MVP; enum later.
* Liquidity scale 0–5 (based on ADV/spread where possible).
* Regime uses multi-indicator posture + manual override logged with provenance.
* **10 agents** in static roster (confirmed in A3).
* Corporate action risk moved to Category F: Data Validity (not staleness).

✅ **Acknowledged Missing Areas (explicitly tracked for HLD scope):**

* Corporate actions handling: MVP flags risk via Category F; full adjustment pipeline later.
* Identifier resolution beyond ticker+exchange: v1.0+.
* Instrument types beyond equities/ETFs: limited MVP support, flag gaps.
* Compliance/tax: informational only, out of scope for automated outputs.

✅ **Assumptions Locked:**

* Manual seeded inputs in v0.1; deterministic orchestration; static 10-agent roster; point-in-time snapshots.

✅ **Risks Documented:**

* Portfolio complexity, FX accuracy, veto ambiguity, override conflicts, NA vs unknown semantics.

---

## TASK 0 COMPLETION CHECKPOINT

**Status:** ✅ Requirements verification complete (portfolio-first, professional-grade)  
**Readiness for HLD:** PROCEED

---

---

# TASK 1 — HIGH LEVEL DESIGN (HLD) — PORTFOLIO-FIRST

## §1) Purpose and Non-Goals

### 1.1 Purpose

Design a **portfolio-first, multi-agent risk assessment system** ("Bridgerton Services") that evaluates a **PortfolioSnapshot** containing N holdings (N≥1) and produces:

1. A **PortfolioCommitteePacket** — portfolio-level risk assessment, aggregated scores, concentration warnings, regime constraints, and position sizing guidance.
2. N **HoldingPacket** outputs — per-holding structured analysis with provenance, uncertainty penalties, and recommendation categories.
3. A **FailedRunPacket** — minimal diagnostic output if orchestrator encounters unrecoverable runtime errors.

The system operates as a **decision-support tool** (not an automated trading bot) with:

* **Risk-first philosophy**: Explicit uncertainty penalties, veto gates, and "no invented numbers" enforcement.
* **Auditability**: Full provenance tracking, deterministic orchestration, reproducible outputs.
* **Governance**: Multi-agent committee with hard veto powers (DIO, Risk Officer) and override authorities (GRRA, LEFO, PSCC) that Chair/Fund Manager cannot circumvent.

### 1.2 Non-Goals (Out of Scope)

* Automated trade execution or brokerage integration
* Real-time streaming data or HFT systems
* Price predictions, alpha guarantees, or financial advice
* Multi-tenant SaaS platform features (auth, billing, HA infrastructure)
* MARL/RL training as core methodology
* Complex derivatives strategies (options, swaps) in MVP
* Natural language chat interface (v0.1 is structured inputs/outputs only)

---

## §2) System Overview and Boundaries

### 2.1 System Boundary

**Inputs (One Run):**

* **PortfolioSnapshot** (required): List of N holdings with weights, cash %, optional theme tags
* **PortfolioConfig** (required if portfolio provided): base_currency, risk_tolerance, concentration_limits
* **RunConfig** (required): run_mode (FAST/DEEP), burn_rate_classification inputs per holding
* **Seeded/Manual Data** (required in v0.1): Financials, price/volume, news, filings, macro indicators — all with SourceRef provenance
* **Optional Inputs**: FX rates (manual), correlation matrix (manual), compliance_flags

**Outputs (One Run):**

* **PortfolioCommitteePacket** (produced if portfolio_run_outcome = COMPLETED):
  * Portfolio-level metrics (aggregate exposure, concentration, liquidity risk, regime constraints)
  * portfolio_run_outcome: COMPLETED / VETOED / SHORT_CIRCUITED / FAILED
  * per_holding_outcomes: map of holding_id → holding_run_outcome
  * Disclaimers and limitations
* **N × HoldingPacket** (one per holding, produced for COMPLETED/VETOED/SHORT_CIRCUITED holdings; omitted for FAILED holdings):
  * 8-dimension scorecard
  * Uncertainty penalties breakdown
  * Risk-adjusted final score
  * Recommendation category (Buy/Increase / Watch / Avoid)
  * Position sizing guidance (constrained by regime + liquidity + portfolio caps)
  * What-to-fetch-next list
  * holding_run_outcome: COMPLETED / VETOED / SHORT_CIRCUITED / FAILED
* **FailedRunPacket** (produced if portfolio_run_outcome = FAILED):
  * run_id, error_type, error_message, traceback
  * Partial outputs if available (e.g., which holdings succeeded before failure)
  * Minimal RunLog
* **RunLog** (always produced): run_id, timestamps, config snapshot, agent outputs, canonical_output_hash (if COMPLETED), error records

### 2.2 Portfolio-First Operating Model

* **Primary Mode**: User provides a PortfolioSnapshot with N≥1 holdings. System evaluates all holdings, aggregates portfolio-level risk, applies portfolio-level veto gates (PSCC concentration, regime constraints, FX exposure).
* **Debug/Single-Holding Mode**: Portfolio with N=1 (treated as a degenerate case; portfolio-level checks still run but trivially pass if only one holding).
* **Partial Failure Policy (R20)**: If ≤30% of holdings FAILED/VETOED, portfolio_run_outcome = COMPLETED with explicit per_holding_outcomes. If >30% fail, portfolio_run_outcome = VETOED or FAILED depending on root cause.

### 2.3 Run Modes

* **FAST**: Minimal agent subset, relaxed staleness thresholds (penalty: 120d financials, 3d price; hard-stop: 365d financials, 30d price), produces triage-level packet.
* **DEEP**: Full agent committee, stricter staleness (penalty: 90d financials, 1d price; hard-stop: 180d financials, 14d price), comprehensive validation gates.

### 2.4 Run Outcome Semantics (R13) — AUTHORITATIVE DEFINITIONS

**Portfolio-Level Outcome (SINGLE SOURCE OF TRUTH):**

RunLog contains **exactly one** outcome field: `portfolio_run_outcome`

Valid values:

* **COMPLETED**: All orchestration phases completed successfully; PortfolioCommitteePacket + HoldingPackets emitted (even if some holdings are VETOED/SHORT_CIRCUITED, as long as ≤30% are FAILED/VETOED).
* **VETOED**: DIO portfolio-level veto (e.g., base_currency missing, critical portfolio data missing, hard-stop staleness threshold exceeded) OR >30% holdings VETOED/FAILED → governance gate triggered, portfolio deemed unreliable.
* **SHORT_CIRCUITED**: GRRA do_not_trade flag = true → macro regime prevents new positions; PortfolioCommitteePacket emitted with all holdings marked SHORT_CIRCUITED and explicit regime constraint note.
* **FAILED**: Orchestrator runtime exception or unrecoverable error (e.g., corrupt input data, agent crash during critical phase, schema validation failure) → FailedRunPacket emitted with diagnostics.

**Holding-Level Outcomes (per_holding_outcomes map):**

Valid values:

* **COMPLETED**: Holding evaluated successfully; scorecard + recommendation produced.
* **VETOED**: DIO hard-stop (missing HardStopFieldRegistry fields, contradictions, integrity failure, staleness hard-stop) OR Risk Officer extreme uncertainty veto → governance gate triggered, holding deemed unreliable.
* **SHORT_CIRCUITED**: GRRA regime prevents evaluation → inherited from portfolio-level short-circuit; HoldingPacket includes regime note, no recommendation.
* **FAILED**: Runtime exception during holding evaluation (e.g., malformed InstrumentIdentity, agent exception) → HoldingPacket omitted or minimal, error logged, other holdings continue.

**Critical Distinctions:**
* **FAILED** = technical failure (bugs, exceptions, corrupt data, schema violations)
* **VETOED** = governance enforcement (data quality gates, integrity checks, registry hard-stops)
* **SHORT_CIRCUITED** = policy override (regime risk constraints, macro crisis prevention)
* **COMPLETED** = success (possibly with warnings/penalties)

**Invariant:** 
* RunLog.portfolio_run_outcome is the canonical run outcome.
* No duplicate or conflicting outcome fields exist.
* PortfolioCommitteePacket.portfolio_run_outcome mirrors RunLog.portfolio_run_outcome (derived, not independent).

---

## §3) Agent Roster, Responsibilities, and Authority Limits

### 3.1 Agent Roster (10 Agents — FIXED)

#### 1) Chair / Fund Manager (Orchestrator, No Veto Override)

* **Responsibilities**: Aggregates agent outputs, applies scoring rubric, enforces governance rules, generates final recommendations.
* **Authority**: Can synthesize, but **cannot override veto gates** from DIO, Risk Officer, or short-circuit from GRRA, or caps from LEFO/PSCC.
* **Outputs**: Final PortfolioCommitteePacket + HoldingPackets.

#### 2) Data Integrity Officer (DIO) — VETO AUTHORITY

* **Responsibilities**:
  * Validate data freshness (staleness checks per R3, C2 — both penalty and hard-stop thresholds)
  * Detect missing critical fields (per HardStopFieldRegistry R14)
  * Identify contradictions in sourced metrics
  * Flag corporate action risks (R17 — Category F: Data Validity)
  * Enforce "no invented numbers" policy (R2)
  * Validate InstrumentIdentity completeness (ticker, exchange, currency per R9)
  * Validate base_currency presence if portfolio provided (R10)
* **Veto Triggers** (HARD STOP → VETOED):
  * Missing fields in HardStopFieldRegistry for relevant instrument type
  * base_currency missing when PortfolioSnapshot provided
  * Contradictions in critical metrics unresolved
  * Data staleness exceeds hard-stop thresholds (mode-dependent, see C2)
  * Unsourced numbers detected in any agent output
* **Outputs**: DIOOutput schema (see §5)

#### 3) Global Risk Regime Architect (GRRA) — SHORT-CIRCUIT AUTHORITY

* **Responsibilities**:
  * Assess macro regime: RISK_ON / NEUTRAL / RISK_OFF / CRISIS
  * Set system-wide risk posture (risk_budget_multiplier, required_checks)
  * Flag do_not_trade conditions (e.g., CRISIS + high volatility)
* **Authority**: If do_not_trade flag = true → entire portfolio_run_outcome = SHORT_CIRCUITED (no new positions allowed).
* **Outputs**: GRRAOutput schema (see §5)

#### 4) Data Ingestion Agent (No Veto)

* **Responsibilities**: Collect, normalize, timestamp all seeded/manual inputs. Generate SourceRef for each metric.
* **Authority**: None (advisory only).
* **Outputs**: Normalized data inventory with provenance.

#### 5) Fundamentals Agent (No Veto)

* **Responsibilities**: Assess financial health, runway, burn rate (if burn-rate company per R15), dilution risk, valuation sanity.
* **Authority**: Suggests penalties for missing/stale fundamentals; no direct veto.
* **Outputs**: AgentResult with fundamentals scorecard contribution.

#### 6) Technical/Market Agent (No Veto)

* **Responsibilities**: Trend analysis, volatility regime, drawdown risk, momentum/reversal signals, technical support/resistance.
* **Authority**: Suggests penalties for low-confidence technicals; no direct veto.
* **Outputs**: AgentResult with technical scorecard contribution.

#### 7) Liquidity & Exit Feasibility Officer (LEFO) — OVERRIDE AUTHORITY

* **Responsibilities**:
  * Assess tradability (liquidity grade 0–5 per C4)
  * Estimate time-to-exit for various position sizes
  * Set max position caps (% of portfolio) based on liquidity
  * Flag exit risks (e.g., penny stocks, thinly traded)
* **Authority**:
  * Liquidity grade 0–1 → HARD OVERRIDE: position cap or Avoid recommendation regardless of score
  * Aggregate portfolio liquidity risk for PSCC
* **Outputs**: LEFOOutput schema (see §5)

#### 8) Portfolio Structure & Concentration Controller (PSCC) — CAP AUTHORITY

* **Responsibilities**:
  * Assess portfolio concentration (single-name, sector, theme, FX exposure)
  * Validate correlation assumptions (if provided)
  * Apply position sizing caps based on concentration limits
  * Aggregate liquidity risk across holdings
* **Authority**: Enforce concentration caps (e.g., no single holding >15%, no sector >30%). Cannot veto entire run but can cap individual positions to zero or Watch-only.
* **Outputs**: PSCCOutput schema (see §5)

#### 9) Risk Officer (VETO AUTHORITY)

* **Responsibilities**:
  * Apply uncertainty penalties (R3)
  * Enforce PenaltyCriticalFieldRegistry checks (R14)
  * Flag FX exposure risks (R11)
  * Detect extreme uncertainty (multiple agents confidence <0.5)
  * Monitor regime constraints from GRRA
* **Veto Triggers** (HARD STOP → VETOED):
  * Extreme uncertainty + CRISIS regime combination
  * FX exposure >threshold without FX rate data (if critical)
  * Cumulative penalties exceed safety threshold (e.g., >-40 after cap)
* **Outputs**: AgentResult with penalty recommendations + veto_flags.

#### 10) Devil's Advocate (No Veto, Mandatory Counter-Case)

* **Responsibilities**: Argue strongest counter-thesis for each holding. Surface unresolved risks.
* **Authority**: If raises unresolved fatal risk → triggers confidence penalty.
* **Outputs**: AgentResult with counter_case narrative.

### 3.2 Veto Precedence Hierarchy (R4, R13) — ABSOLUTE

When multiple override conditions exist, apply in strict order:

1. **DIO VETOED** (highest precedence): Data integrity failure → portfolio or holding VETOED
2. **GRRA SHORT_CIRCUITED**: do_not_trade flag → portfolio SHORT_CIRCUITED (no new positions)
3. **LEFO position caps**: Liquidity constraints → capped position or Avoid
4. **PSCC concentration caps**: Portfolio limits → capped position or Watch
5. **Risk Officer penalties/confidence downgrades**: Applied after above
6. **Chair aggregation**: Cannot override any of 1–5

**Invariant**: Lower-numbered items always override higher-numbered items.

---

## §4) Orchestration Flow

### 4.1 End-to-End Sequence (Portfolio-First, DEEP Mode)

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 0: INTAKE & VALIDATION                                     │
└─────────────────────────────────────────────────────────────────┘
0.1) Generate run_id (UUID)
0.2) Load PortfolioSnapshot, PortfolioConfig, RunConfig, seeded data
0.3) Validate PortfolioConfig.base_currency present (if portfolio provided)
     → If missing: DIO VETO → portfolio_run_outcome = VETOED
        - Emit minimal PortfolioCommitteePacket with veto note
        - Emit RunLog
        - STOP
0.4) Validate InstrumentIdentity for all holdings (ticker, exchange, currency)
     → If invalid/malformed/schema-noncompliant:
        - Mark holding_run_outcome = FAILED (not VETOED — schema violation = technical failure)
        - Log error to RunLog
        - CONTINUE with valid holdings
0.5) Initialize RunLog with config snapshot, input_snapshot_hash
0.6) Error Handling Gate:
     → If unrecoverable exception in Phase 0 (e.g., RunConfig malformed, schema invalid):
        - Set portfolio_run_outcome = FAILED
        - Emit FailedRunPacket with error details
        - Finalize RunLog
        - STOP

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: PORTFOLIO-LEVEL PRE-FLIGHT (GRRA + DIO)                │
└─────────────────────────────────────────────────────────────────┘
1.1) GRRA: Assess macro regime
     → Output: regime_label, confidence, risk_budget_multiplier, do_not_trade flag
     → If do_not_trade = true:
        - Set portfolio_run_outcome = SHORT_CIRCUITED
        - Set all holdings to holding_run_outcome = SHORT_CIRCUITED
        - Generate PortfolioCommitteePacket with regime constraint note
        - Generate HoldingPackets for all holdings (with SHORT_CIRCUITED status, no recommendations)
        - Finalize RunLog
        - STOP

1.2) DIO: Portfolio-level staleness check on macro/regime inputs
     → If stale beyond penalty threshold: apply portfolio-level penalty (logged)
     → If stale beyond hard-stop threshold: DIO VETO
        - Set portfolio_run_outcome = VETOED
        - Emit minimal PortfolioCommitteePacket with veto note
        - STOP

1.3) DIO: Validate FX rates if base_currency != holding currencies
     → If FX rates missing: flag FX_EXPOSURE_RISK
     → If FX rates stale beyond hard-stop threshold (FAST >7d, DEEP >48h): DIO VETO
        - Set portfolio_run_outcome = VETOED
        - Emit minimal PortfolioCommitteePacket with veto note
        - STOP
     → If stale beyond penalty threshold but within hard-stop: suggest penalty

1.4) Log GRRA + DIO outputs to RunLog

1.5) Error Handling Gate:
     → If agent exception in Phase 1:
        - Set portfolio_run_outcome = FAILED
        - Emit FailedRunPacket
        - STOP

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: PER-HOLDING EVALUATION LOOP (Deterministic Order)      │
└─────────────────────────────────────────────────────────────────┘

Holdings are processed in STABLE SORTED ORDER by holding_id (lexicographic).

FOR EACH holding in PortfolioSnapshot (sorted by holding_id):

  2.1) Data Ingestion Agent: Normalize holding-specific data
       → Generate SourceRef for all metrics
       → Detect missing/stale fields
       → Error Handling: If agent crashes → mark holding_run_outcome = FAILED, log error, CONTINUE

  2.2) DIO: Holding-level validation
       → Check HardStopFieldRegistry (based on RunConfig burn-rate classification R15):
          - Identity fields (ticker, exchange, currency) ALWAYS hard-stop if missing
          - If is_burn_rate_company = true: cash, runway, burn_rate are HARD-STOP
          - Else if is_burn_rate_company = false: cash/runway are PENALTY-CRITICAL only
          - Else if not_applicable = true (e.g., banks): cash/runway are IGNORED (no penalty)
       → Check PenaltyCriticalFieldRegistry (shares, price, volume, etc.)
       → Check staleness:
          - If beyond hard-stop threshold → DIO VETO
          - If beyond penalty threshold but within hard-stop → suggest penalty
       → Detect contradictions
       → Flag corporate_action_risk (R17 — Category F: Data Validity) if recent splits/dividends detected
       → If HARD-STOP field missing OR staleness hard-stop triggered OR integrity failure:
          - Set holding_run_outcome = VETOED
          - Generate HoldingPacket with VETOED status + limitations
          - Log to RunLog
          - SKIP remaining agents for this holding, CONTINUE to next holding
       → Error Handling: If DIO crashes → holding_run_outcome = FAILED, CONTINUE

  2.3) Fundamentals Agent: Assess financial health
       → Score dimension 1 (Financial Strength & Dilution Risk)
       → Flag missing/stale fundamentals → suggest penalties
       → Output: AgentResult
       → Error Handling: If crashes → holding_run_outcome = FAILED, CONTINUE

  2.4) Technical/Market Agent: Assess trend, volatility, momentum
       → Score dimension 2 (Asset Quality & Technical De-Risking)
       → Score dimension 5 (Market/Technical Risk & Volatility Profile)
       → Output: AgentResult
       → Error Handling: If crashes → holding_run_outcome = FAILED, CONTINUE

  2.5) LEFO: Assess liquidity
       → Calculate liquidity_grade (0–5)
       → Estimate time_to_exit
       → Set max_position_cap (% of portfolio)
       → If liquidity_grade ≤1: set HARD OVERRIDE flag
       → Score dimension 6 (Liquidity & Exit Feasibility)
       → Output: LEFOOutput
       → Error Handling: If crashes → holding_run_outcome = FAILED, CONTINUE

  2.6) Devil's Advocate: Counter-thesis (DEEP mode only)
       → Argue strongest risks for this holding
       → If unresolved fatal risk: flag confidence penalty
       → Output: AgentResult
       → Error Handling: If crashes → log warning, CONTINUE (optional agent)

  2.7) Risk Officer: Apply penalties
       → Calculate penalties per categories (A, B, C, D, E, F) — see §7.4
       → Enforce -35 cap (DEEP) or -40 cap (FAST)
       → If extreme uncertainty + CRISIS: set holding_run_outcome = VETOED
       → Output: AgentResult with penalty breakdown
       → Error Handling: If crashes → holding_run_outcome = FAILED, CONTINUE

  2.8) Chair: Aggregate holding score
       → BaseScore = Σ( (DimensionScore_i / 5) * Weight_i )
       → FinalScore = clamp(BaseScore - TotalPenalties, 0, 100)
       → Apply LEFO hard override if needed
       → Map to recommendation category (see §7.5)
       → Set holding_run_outcome = COMPLETED (unless vetoed earlier or FAILED)
       → Generate HoldingPacket
       → Log to RunLog
       → Error Handling: If Chair crashes on this holding → holding_run_outcome = FAILED, CONTINUE

END LOOP

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: PORTFOLIO-LEVEL AGGREGATION (PSCC + Chair)             │
└─────────────────────────────────────────────────────────────────┘
3.1) PSCC: Assess portfolio structure
     → Calculate concentration by name, sector, theme, FX exposure
     → Validate against PortfolioConfig.concentration_limits
     → If breaches detected: apply position caps or downgrade to Watch
     → Aggregate liquidity risk across holdings
     → Output: PSCCOutput
     → Error Handling: If PSCC crashes → portfolio_run_outcome = FAILED, emit FailedRunPacket, STOP

3.2) Chair: Normalize holdings to base_currency
     → Apply FX rates (with SourceRef + timestamp)
     → Calculate portfolio-level exposures
     → Apply PSCC caps to position sizing guidance
     → Error Handling: If Chair crashes → portfolio_run_outcome = FAILED, emit FailedRunPacket, STOP

3.3) Chair: Determine portfolio_run_outcome (R20)
     → Count holdings by outcome: COMPLETED, VETOED, FAILED, SHORT_CIRCUITED
     → If >30% VETOED or FAILED: set portfolio_run_outcome = VETOED
     → Else: set portfolio_run_outcome = COMPLETED
     → Generate PortfolioCommitteePacket with per_holding_outcomes

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: CANONICALIZATION & LOGGING (R16)                        │
└─────────────────────────────────────────────────────────────────┘
4.1) Apply canonicalization rules (see §6):
     → Stable sort all arrays:
        - holdings by holding_id (lexicographic)
        - penalties by category then reason (lexicographic)
        - agent_outputs by agent_name (lexicographic)
        - veto_logs by timestamp then agent_name
     → Exclude equivalence fields from hash:
        - run_id
        - all timestamp fields (start_time, end_time, generated_at, retrieval_timestamp)
        - duration_seconds
        - narrative text fields (notes, disclaimers, limitations)
        - agent execution timing metadata

4.2) Compute canonical_output_hash (deterministic hash of core decision fields)
     → Only if portfolio_run_outcome = COMPLETED
     → Include: portfolio snapshot, config, seeded data values (not retrieval times), 
               all scores, penalties, recommendations, veto events, regime, caps

4.3) Finalize RunLog with:
     → portfolio_run_outcome (SINGLE SOURCE OF TRUTH)
     → per_holding_outcomes map
     → agent outputs, timestamps
     → canonical_output_hash (if COMPLETED)
     → input_snapshot_hash

4.4) Emit final output:
     → If portfolio_run_outcome = COMPLETED: PortfolioCommitteePacket + HoldingPackets + RunLog
     → If portfolio_run_outcome = VETOED: Minimal PortfolioCommitteePacket + RunLog
     → If portfolio_run_outcome = SHORT_CIRCUITED: PortfolioCommitteePacket + HoldingPackets (all SHORT_CIRCUITED) + RunLog
     → If portfolio_run_outcome = FAILED: FailedRunPacket + RunLog
```

### 4.2 FAST Mode Differences

* **Agent Subset**: Skip Devil's Advocate, reduce validation gates
* **Staleness Thresholds**:
  * Penalty: 120d financials, 3d price, 14d macro
  * Hard-stop: 365d financials, 30d price, 90d macro
* **Penalty Caps**: -40 total (vs -35 in DEEP)
* **Outcome**: Produces triage-level packet; suitable for quick screening

### 4.3 Deterministic Ordering Requirements (R16)

All arrays and collections must be sorted using stable, deterministic ordering:

* **Holdings**: Sort by holding_id (lexicographic, case-sensitive)
* **Agent outputs**: Sort by agent_name (lexicographic)
* **Penalties**: Sort by category (A, B, C, D, E, F) then by reason (lexicographic)
* **Veto logs**: Sort by timestamp then agent_name
* **Dict keys**: Always serialize in sorted order (JSON canonical form)

**Invariant**: Two runs with identical logical inputs must produce identical canonical_output_hash.

---

## §5) Data Models and Contracts (Field Lists — DESIGN ONLY)

### 5.1 Core Schemas

#### InstrumentIdentity (R9)

* ticker: string, required
* exchange: string, required (free-form in v0.1)
* country: string, optional (ISO code)
* currency: string, required (ISO code e.g., USD, NZD, EUR)
* isin: string, optional
* instrument_type: string (e.g., "common_stock", "etf", "adr")
* share_class: string, optional (e.g., "A", "B")

#### SourceRef (R2)

* origin: string (e.g., "manual_paste", "local_csv", "user_upload")
* as_of_date: datetime, required (tz-aware UTC)
* retrieval_timestamp: datetime, required (tz-aware UTC)
* original_timezone: string, optional (for transparency)
* provider_name: string, optional (e.g., "Yahoo Finance")
* provider_version: string, optional
* notes: string, optional

#### MetricValue (R2, R3)

* value: optional float / string / bool
* unit: optional string (e.g., "USD", "shares", "percentage")
* missing_reason: optional string (if value = None, e.g., "data unavailable", "not disclosed")
* not_applicable: bool, default False (for instrument-type mismatch, e.g., burn_rate for banks)
* source_ref: SourceRef, required if value provided

**Semantic Rules:**
* If `not_applicable = true`: field is irrelevant for this instrument/sector → NO PENALTY
* If `value = None AND missing_reason set`: unknown/missing → PENALTY if field is critical
* If `value = None AND not_applicable = false AND missing_reason = None`: SCHEMA VIOLATION → FAILED

#### AgentResult (R5)

* agent_name: string
* status: string ("completed", "failed", "skipped")
* confidence: float (0.0–1.0)
* key_findings: dict (structured, schema varies by agent)
* metrics: list of MetricValue (all metrics with provenance)
* suggested_penalties: list of PenaltyItem
* veto_flags: list of string (e.g., ["HARD_STOP_MISSING_CASH"])
* counter_case: optional string (Devil's Advocate only)
* notes: string, optional

#### GRRAOutput (extends AgentResult) (R4)

* regime_label: string ("RISK_ON" | "NEUTRAL" | "RISK_OFF" | "CRISIS")
* regime_confidence: float (0.0–1.0)
* risk_budget_multiplier: float (e.g., 0.5 for RISK_OFF, 0.2 for CRISIS)
* required_checks: list of string (e.g., ["require_deep_mode"])
* do_not_trade_flag: bool, default False
* regime_indicators: dict (VIX, credit spreads, etc. with SourceRef)

#### DIOOutput (extends AgentResult) (R14, R17)

* data_confidence: float (0.0–1.0, overall)
* staleness_flags: list of StalenessFlag
* missing_hard_stop_fields: list of string
* missing_penalty_critical_fields: list of string
* contradictions: list of ContradictionRecord
* corporate_action_risk: optional CorporateActionRisk
* unsourced_numbers_detected: bool
* integrity_veto_triggered: bool

**StalenessFlag:**
* field_name: string
* age_days: int
* penalty_threshold_days: int
* hard_stop_threshold_days: int
* penalty_suggested: float
* hard_stop_triggered: bool

**ContradictionRecord:**
* field_name: string
* source_1: SourceRef
* value_1: any
* source_2: SourceRef
* value_2: any
* resolution: optional string

**CorporateActionRisk (R17 — Category F: Data Validity):**
* event_type: string ("split", "reverse_split", "dividend", "spinoff", "merger")
* event_date: datetime
* adjustment_factor: optional float
* metrics_affected: list of string
* penalty_suggested: float (goes to Category F, not Category B)

#### LEFOOutput (extends AgentResult) (R4)

* liquidity_grade: int (0–5)
* adv_usd: optional float (average daily volume in USD)
* bid_ask_spread_bps: optional float
* time_to_exit_estimate: optional string (e.g., "<1 day", "2–5 days")
* max_position_cap_pct: float (% of portfolio, e.g., 5.0)
* exit_risk_warnings: list of string
* hard_override_triggered: bool (if liquidity_grade ≤1)

#### PSCCOutput (extends AgentResult) (R19)

* concentration_by_name: dict (holding_id → weight %)
* concentration_by_sector: dict (sector → weight %)
* concentration_by_theme: dict (theme → weight %)
* fx_exposure_by_currency: dict (currency → weight %)
* correlation_matrix: optional list of list of float (if provided)
* concentration_breaches: list of ConcentrationBreach
* position_caps_applied: dict (holding_id → capped weight %)
* portfolio_liquidity_risk: string ("low", "medium", "high")

**ConcentrationBreach:**
* breach_type: string ("single_name", "sector", "theme", "fx")
* identifier: string
* current_weight_pct: float
* limit_pct: float
* action_taken: string ("capped", "watch_only", "avoid")

#### Scorecard (R1)

* dimension_scores: dict (dimension_name → DimensionScore)
* base_score: float (0–100)
* penalty_breakdown: PenaltyBreakdown
* final_score: float (0–100, after penalties)

**DimensionScore:**
* dimension_name: string
* raw_score: int (0–5)
* weight: float (e.g., 18.0 for dimension 1)
* contribution: float (= raw_score / 5 × weight)
* confidence: float (0.0–1.0)
* notes: string

**PenaltyBreakdown (R17 — Updated with Category F):**
* category_A_missing_critical: float (0 to -20)
* category_B_staleness: float (0 to -10)
* category_C_contradictions_integrity: float (0 to -20)
* category_D_confidence: float (0 to -10)
* category_E_fx_exposure_risk: float (0 to -10)
* category_F_data_validity: float (0 to -10) — NEW: Corporate actions, data quality issues
* total_penalties: float (capped at -35 DEEP or -40 FAST)
* details: list of PenaltyItem

**PenaltyItem:**
* category: string ("A", "B", "C", "D", "E", "F")
* reason: string
* amount: float (negative)
* source_agent: string

#### HoldingPacket (R8)

* holding_id: string
* instrument: InstrumentIdentity
* holding_run_outcome: string ("COMPLETED" | "VETOED" | "SHORT_CIRCUITED" | "FAILED")
* scorecard: Scorecard (if COMPLETED or VETOED; omitted if FAILED or SHORT_CIRCUITED)
* recommendation_category: string ("Buy/Increase" | "Watch" | "Avoid") (if COMPLETED only)
* position_sizing_guidance: PositionSizingGuidance (if COMPLETED only)
* what_to_fetch_next: list of string
* limitations: list of string
* disclaimers: string (standard legal text)
* agent_outputs: dict (agent_name → AgentResult summary) (if COMPLETED or VETOED)

**PositionSizingGuidance:**
* recommended_weight_pct: optional float (% of portfolio)
* min_weight_pct: optional float
* max_weight_pct: optional float (constrained by LEFO + PSCC)
* regime_constraint: string (e.g., "crisis: no new positions")
* liquidity_constraint: string (e.g., "max 2% due to low ADV")
* concentration_constraint: optional string
* fx_exposure_note: optional string

#### PortfolioCommitteePacket (R8)

* run_id: string (UUID)
* portfolio_run_outcome: string ("COMPLETED" | "VETOED" | "SHORT_CIRCUITED" | "FAILED") — mirrors RunLog
* per_holding_outcomes: dict (holding_id → holding_run_outcome)
* portfolio_config: PortfolioConfig
* portfolio_snapshot: PortfolioSnapshot
* grra_output: GRRAOutput
* pscc_output: PSCCOutput (if portfolio_run_outcome = COMPLETED)
* portfolio_level_metrics: PortfolioMetrics (if portfolio_run_outcome = COMPLETED)
* holding_packets: list of HoldingPacket
* limitations: list of string
* disclaimers: string
* canonical_output_hash: string (only if portfolio_run_outcome = COMPLETED, for reproducibility R16)
* generated_at: datetime (tz-aware UTC)

**PortfolioMetrics:**
* total_portfolio_value_base_currency: optional float
* fx_normalized_exposures: dict (currency → value in base_currency)
* aggregate_concentration: dict (sector → weight %)
* aggregate_liquidity_risk: string
* regime_adjusted_risk_budget: float

#### FailedRunPacket (NEW — R13)

* run_id: string (UUID)
* portfolio_run_outcome: string ("FAILED")
* error_type: string (e.g., "orchestrator_exception", "agent_crash", "schema_validation_error", "input_corruption")
* error_message: string
* error_timestamp: datetime (tz-aware UTC)
* traceback: optional string
* partial_outputs: optional dict (e.g., {"completed_holdings": [...], "failed_at_phase": "2.3", "failed_at_holding": "ABC"})
* run_log_summary: RunLog (minimal, with error records)
* recovery_suggestions: list of string (e.g., ["Check input data format", "Validate PortfolioConfig schema"])

#### PortfolioConfig (R6, R10)

* base_currency: string, required if portfolio provided (ISO code)
* risk_tolerance: string ("conservative" | "moderate" | "aggressive")
* concentration_limits: ConcentrationLimits
* theme_tags: optional dict (holding_id → list of themes)
* compliance_flags: optional dict (holding_id → list of restrictions)

**ConcentrationLimits:**
* max_single_name_pct: float, default 15.0
* max_sector_pct: float, default 30.0
* max_theme_pct: optional float
* max_fx_exposure_pct: optional float

#### PortfolioSnapshot (R6)

* snapshot_date: datetime (tz-aware UTC)
* holdings: list of Holding
* cash_pct: float (% of portfolio in cash)
* total_value_base_currency: optional float

**Holding:**
* holding_id: string (unique within portfolio)
* instrument: InstrumentIdentity
* current_weight_pct: float
* current_value_base_currency: optional float
* acquisition_date: optional datetime
* theme_tags: optional list of string
* compliance_flags: optional list of string

#### RunConfig (R7, R15)

* run_mode: string ("FAST" | "DEEP")
* burn_rate_classification: dict (holding_id → BurnRateClassification)
* staleness_thresholds: StalenessThresholds (mode-specific defaults)
* penalty_caps: PenaltyCaps (mode-specific)
* custom_overrides: optional dict

**BurnRateClassification (R15):**
* is_burn_rate_company: optional bool (if true: cash/runway/burn → HARD-STOP)
* not_applicable: optional bool (if true: cash/runway/burn → IGNORED, e.g., banks, insurers)
* company_stage: optional string ("startup", "growth", "mature")
* notes: optional string

**Semantic Rules:**
* If `is_burn_rate_company = true`: cash, runway, burn_rate in HardStopFieldRegistry
* If `not_applicable = true`: cash, runway, burn_rate IGNORED (not penalized, not vetoed)
* If both false/None: cash, runway in PenaltyCriticalFieldRegistry (missing → penalty, not veto)
* Cannot have both `is_burn_rate_company = true` AND `not_applicable = true` (schema violation)

**StalenessThresholds (C2):**
* financials_penalty_max_age_days: int (FAST 120, DEEP 90)
* financials_hard_stop_max_age_days: int (FAST 365, DEEP 180)
* price_volume_penalty_max_age_days: int (FAST 3, DEEP 1)
* price_volume_hard_stop_max_age_days: int (FAST 30, DEEP 14)
* company_updates_penalty_max_age_days: int (FAST 90, DEEP 60)
* macro_regime_penalty_max_age_days: int (FAST 14, DEEP 7)
* macro_regime_hard_stop_max_age_days: int (FAST 90, DEEP 30)
* fx_rate_hard_stop_max_age_days: int (FAST 7, DEEP 2)

**PenaltyCaps:**
* total_penalty_cap: float (FAST -40.0, DEEP -35.0)
* category_A_cap: float (-20.0)
* category_B_cap: float (-10.0)
* category_C_cap: float (-20.0)
* category_D_cap: float (-10.0)
* category_E_cap: float (-10.0)
* category_F_cap: float (-10.0)

#### ConfigSnapshot (R14)

* hard_stop_field_registry: HardStopFieldRegistry
* penalty_critical_field_registry: PenaltyCriticalFieldRegistry
* scoring_rubric_version: string (e.g., "v1.0")
* agent_prompt_versions: dict (agent_name → version)

**HardStopFieldRegistry (R14 — REVISED):**

Fields in this registry trigger immediate VETOED if missing (no penalties, instant veto).

* identity_fields_all_companies: list of string
  - ["ticker", "exchange", "currency"]
  - ALWAYS required for every holding

* burn_rate_fields_conditional: list of string
  - ["cash", "runway_months", "burn_rate"]
  - Required ONLY if RunConfig.burn_rate_classification[holding_id].is_burn_rate_company = true
  - IGNORED if not_applicable = true

* portfolio_level_fields: list of string
  - ["base_currency"]
  - Required at portfolio level if PortfolioSnapshot provided

**PenaltyCriticalFieldRegistry (R14 — REVISED):**

Fields in this registry trigger penalties if missing (execution continues unless thresholds exceeded).

* fundamentals: list of string
  - ["shares_outstanding", "fully_diluted_shares", "market_cap", "revenue", "earnings", "total_debt", "shareholders_equity"]

* fundamentals_conditional_burn_rate: list of string
  - ["cash", "runway_months", "burn_rate"]
  - Penalty-critical ONLY if is_burn_rate_company = false AND not_applicable = false

* technicals: list of string
  - ["price", "volume", "52w_high", "52w_low", "beta"]

* liquidity: list of string
  - ["adv_usd", "bid_ask_spread_bps"]

* macro_regime: list of string
  - ["regime_label", "vix", "credit_spreads", "market_breadth"]

**CRITICAL DISTINCTION:**
* Identity fields (ticker, exchange, currency) are NEVER in PenaltyCriticalFieldRegistry
* They are ONLY in HardStopFieldRegistry
* Missing identity → VETOED (not penalized)

#### RunLog (R13, R16)

* run_id: string (UUID)
* portfolio_run_outcome: string ("COMPLETED" | "VETOED" | "SHORT_CIRCUITED" | "FAILED") — SINGLE SOURCE OF TRUTH
* per_holding_outcomes: dict (holding_id → holding_run_outcome)
* run_mode: string
* config_snapshot: ConfigSnapshot
* input_snapshot_hash: string (hash of PortfolioSnapshot + RunConfig + seeded data)
* canonical_output_hash: optional string (hash of deterministic decision fields R16, only if portfolio_run_outcome = COMPLETED)
* agent_execution_log: list of AgentExecutionRecord
* start_time: datetime (tz-aware UTC)
* end_time: datetime (tz-aware UTC)
* duration_seconds: float
* errors: list of ErrorRecord

**AgentExecutionRecord:**
* agent_name: string
* holding_id: optional string (null for portfolio-level agents)
* start_time: datetime
* end_time: datetime
* status: string
* output_summary: dict

**ErrorRecord:**
* timestamp: datetime
* error_type: string
* error_message: string
* holding_id: optional string
* agent_name: optional string
* traceback: optional string

---

## §6) State, Storage, Audit Logging, and Versioning Design

### 6.1 State Management (In-Memory, Deterministic)

* **Run Scope**: Each run is self-contained; no persistent state between runs.
* **Holding Loop State**: Deterministic ordered iteration (sorted by holding_id).
* **Agent State**: Agents are stateless; inputs/outputs are pure functions of provided data.

### 6.2 Audit Logging (RunLog Contents)

Every run produces a RunLog containing:

* **Inputs Snapshot**: PortfolioSnapshot, PortfolioConfig, RunConfig, seeded data (hashed via input_snapshot_hash)
* **Config Snapshot**: Rubric version, agent prompt versions, registry versions
* **Agent Execution Log**: Timestamped record of every agent invocation (holding-level + portfolio-level)
* **Veto/Override Events**: All veto triggers, GRRA short-circuits, LEFO/PSCC caps
* **Outputs Snapshot**: PortfolioCommitteePacket + HoldingPackets (hashed via canonical_output_hash if COMPLETED)
* **Errors**: All exceptions, validation failures, missing data warnings, FAILED holding details

### 6.3 Versioning Strategy

* **Schema Versioning**: Each schema includes a `schema_version` field (e.g., "v1.0.0").
* **Rubric Versioning**: Scorecard weights + penalty rules versioned; stored in ConfigSnapshot.
* **Agent Prompt Versioning**: If LLM agents used later, prompts are versioned and logged.
* **Backward Compatibility**: Design schemas to allow optional fields; new fields default to None.

### 6.4 Reproducibility & Canonicalization (R16)

#### 6.4.1 Canonicalization Rules (EXPLICIT)

To ensure deterministic outputs for identical logical inputs:

**1. Stable Sorting (MANDATORY):**

All arrays must be sorted using deterministic, stable sort algorithms:

* **Holdings**: Sort by `holding_id` (lexicographic, case-sensitive, UTF-8)
* **Penalties**: Sort by `category` (A, B, C, D, E, F) then by `reason` (lexicographic)
* **Agent outputs**: Sort by `agent_name` (lexicographic)
* **Veto logs**: Sort by `timestamp` (ascending) then by `agent_name` (lexicographic)
* **All dict keys**: Serialize in sorted order (JSON canonical form with `sort_keys=True`)
* **Concentration breaches**: Sort by `breach_type` then by `identifier`

**2. Excluded Fields from Hash (Equivalence Fields):**

These fields do NOT affect decision logic and are excluded from canonical_output_hash:

* `run_id` (unique per run)
* All `timestamp` fields:
  - `start_time`, `end_time`, `generated_at`
  - `retrieval_timestamp` (but `as_of_date` IS INCLUDED)
  - All agent execution timing fields
* `duration_seconds`
* Narrative text fields:
  - `notes` (unless they directly affect scoring)
  - `disclaimers`
  - `limitations`
  - `recovery_suggestions`
* Agent execution logs (timing metadata only; output summaries ARE INCLUDED)

**3. Included Fields in Canonical Hash:**

Core decision fields that MUST match for reproducibility:

* PortfolioSnapshot (holdings sorted by holding_id, weights, cash_pct)
* PortfolioConfig (base_currency, limits, all sorted)
* RunConfig (mode, burn_rate_classification, all sorted)
* Seeded data values:
  - All `as_of_date` fields (included)
  - All `value` fields from MetricValue (included)
  - `retrieval_timestamp` excluded
* All dimension scores, raw_score, weight, contribution
* All penalties (category, reason, amount)
* All final scores
* All veto flags, override flags
* Recommendation categories
* Position sizing caps (max_weight_pct, etc.)
* GRRA regime_label, regime_confidence
* LEFO liquidity_grade, max_position_cap_pct
* PSCC concentration_breaches, position_caps_applied
* per_holding_outcomes (all holding run outcomes)

**4. Hash Algorithm (Conceptual):**

```
canonical_fields = extract_and_sort(
  portfolio_snapshot,
  portfolio_config,
  run_config,
  seeded_data_values,  # excluding retrieval_timestamp
  grra_output (regime, confidence, do_not_trade),
  per_holding_scorecards (sorted by holding_id),
  per_holding_recommendations (sorted by holding_id),
  pscc_caps (sorted),
  veto_events (sorted by timestamp, agent_name)
)

canonical_json = json.dumps(
  canonical_fields,
  sort_keys=True,
  separators=(',', ':')  # no whitespace
)

canonical_output_hash = SHA256(canonical_json.encode('utf-8')).hexdigest()
```

**5. Input Snapshot Hash (Separate):**

```
input_fields = extract_and_sort(
  portfolio_snapshot,
  portfolio_config,
  run_config,
  seeded_data (all fields including retrieval_timestamp)
)

input_snapshot_hash = SHA256(json.dumps(input_fields, sort_keys=True).encode('utf-8')).hexdigest()
```

**Invariant**: Two runs with identical logical inputs (same holdings, same config, same as_of_dates, same values) MUST produce identical canonical_output_hash.

#### 6.4.2 Reproducibility Tests (DESIGN ONLY)

* **Test Case R1**: Run same portfolio + config + data twice → canonical_output_hash IDENTICAL
* **Test Case R2**: Run with different retrieval_timestamp but same as_of_date → canonical_output_hash IDENTICAL
* **Test Case R3**: Run with holdings in different input order → canonical_output_hash IDENTICAL (after sorting)
* **Test Case R4**: Run with added narrative note (excluded field) → canonical_output_hash IDENTICAL
* **Test Case R5**: Run with different run_id → canonical_output_hash IDENTICAL

### 6.5 Data Retention Policy

* **Recommended Default**: Retain RunLog + packets for 7 years (financial record standard).
* **Compression**: After 90 days, compress older runs.
* **Deletion Policy**: Never delete without explicit user request + confirmation.
* **Replay Capability**: Store inputs + config snapshot to enable full replay of any historical run.

---

## §7) Error Handling, Unknown/Stale Policy, and Penalty Rules

### 7.1 Run Outcome Semantics (R13) — AUTHORITATIVE TAXONOMY

**Portfolio-Level Outcome (RunLog.portfolio_run_outcome — SINGLE SOURCE):**

* **COMPLETED**: 
  - All orchestration phases completed successfully
  - PortfolioCommitteePacket + HoldingPackets emitted
  - Allowed even if some holdings are VETOED/SHORT_CIRCUITED (as long as ≤30% are FAILED/VETOED)
  - canonical_output_hash generated

* **VETOED**: 
  - DIO portfolio-level veto (base_currency missing, portfolio staleness hard-stop, FX hard-stop) OR
  - >30% holdings VETOED/FAILED → governance gate triggered
  - Minimal PortfolioCommitteePacket emitted with veto note
  - No canonical_output_hash

* **SHORT_CIRCUITED**: 
  - GRRA do_not_trade flag = true
  - Macro regime prevents new positions
  - PortfolioCommitteePacket emitted with all holdings marked SHORT_CIRCUITED
  - HoldingPackets include regime note, no recommendations
  - No canonical_output_hash

* **FAILED**: 
  - Orchestrator runtime exception
  - Unrecoverable error (corrupt input, schema violation, agent crash in critical phase)
  - FailedRunPacket emitted with diagnostics
  - No PortfolioCommitteePacket or HoldingPackets
  - No canonical_output_hash

**Holding-Level Outcomes (per_holding_outcomes[holding_id]):**

* **COMPLETED**: 
  - Holding evaluated successfully
  - Scorecard + recommendation produced
  - HoldingPacket complete

* **VETOED**: 
  - DIO hard-stop (missing HardStopFieldRegistry fields, contradictions, staleness hard-stop) OR
  - Risk Officer extreme uncertainty veto
  - HoldingPacket includes veto note, no recommendation
  - Scorecard may be partial

* **SHORT_CIRCUITED**: 
  - GRRA regime prevents evaluation (inherited from portfolio-level)
  - HoldingPacket includes regime note
  - No scorecard, no recommendation

* **FAILED**: 
  - Runtime exception during holding evaluation (malformed identity, agent crash)
  - HoldingPacket omitted or minimal
  - Error logged to RunLog
  - Other holdings continue

**Critical Distinctions:**
* **FAILED** = technical/runtime failure (bugs, exceptions, schema violations, corrupt data)
* **VETOED** = governance enforcement (data quality gates, registry hard-stops, integrity checks)
* **SHORT_CIRCUITED** = policy override (regime constraints, macro crisis prevention)
* **COMPLETED** = success (possibly with warnings, penalties, or limitations)

**Invariant**: 
* RunLog.portfolio_run_outcome is the SINGLE canonical run outcome field
* PortfolioCommitteePacket.portfolio_run_outcome mirrors (derives from) RunLog.portfolio_run_outcome
* No duplicate or conflicting outcome fields exist

### 7.2 HardStopFieldRegistry vs PenaltyCriticalFieldRegistry (R14) — REVISED

#### HardStopFieldRegistry (Missing → Immediate VETOED, No Penalties)

**Identity Fields (ALL companies, ALWAYS required):**
* `ticker`
* `exchange`
* `currency`

**Burn-Rate Fields (CONDITIONAL — only if is_burn_rate_company = true):**
* `cash`
* `runway_months`
* `burn_rate`

**Portfolio-Level Fields (if PortfolioSnapshot provided):**
* `base_currency`

**Enforcement**: 
* DIO checks at intake (Phase 0.3 for portfolio, Phase 2.2 for holdings)
* If ANY field missing → holding_run_outcome = VETOED (or portfolio_run_outcome = VETOED for portfolio fields)
* NO PENALTY applied — instant veto

**CRITICAL RULE**: Identity fields (ticker, exchange, currency) are NEVER in PenaltyCriticalFieldRegistry. They are ONLY in HardStopFieldRegistry.

#### PenaltyCriticalFieldRegistry (Missing → Category A Penalty, Execution Continues)

**Fundamentals (ALL companies):**
* `shares_outstanding`
* `fully_diluted_shares`
* `market_cap`
* `revenue`
* `earnings`
* `total_debt`
* `shareholders_equity`

**Fundamentals (CONDITIONAL — only if is_burn_rate_company = false AND not_applicable = false):**
* `cash`
* `runway_months`
* `burn_rate`

**Technicals:**
* `price`
* `volume`
* `52w_high`
* `52w_low`
* `beta`

**Liquidity:**
* `adv_usd`
* `bid_ask_spread_bps`

**Macro/Regime:**
* `regime_label`
* `vix` (or volatility proxy)
* `credit_spreads`
* `market_breadth`

**Enforcement**: 
* Risk Officer applies Category A penalties for missing fields
* Execution continues unless cumulative penalties exceed cap
* If penalties > cap AND high uncertainty → Risk Officer may trigger veto

**Burn-Rate Field Logic (R15):**

| is_burn_rate_company | not_applicable | cash/runway/burn Treatment |
|---------------------|----------------|---------------------------|
| true                | N/A            | HardStopFieldRegistry (missing → VETOED) |
| false               | false          | PenaltyCriticalFieldRegistry (missing → penalty) |
| N/A                 | true           | IGNORED (not penalized, not vetoed) |
| true                | true           | SCHEMA VIOLATION → FAILED |

### 7.3 Staleness Policy (R3, C2) — Dual Thresholds

**Staleness Penalty Thresholds** (triggers penalties, not veto):

| Data Type | FAST Mode | DEEP Mode |
|-----------|-----------|-----------|
| Financials | >120 days | >90 days |
| Price/Volume | >3 days | >1 day |
| Company Updates | >90 days | >60 days |
| Macro/Regime | >14 days | >7 days |

**Staleness Hard-Stop Thresholds** (triggers DIO veto):

| Data Type | FAST Mode | DEEP Mode |
|-----------|-----------|-----------|
| Financials | >365 days | >180 days |
| Price/Volume | >30 days | >14 days |
| Macro/Regime | >90 days | >30 days |
| FX Rates | >7 days | >48 hours |

**Enforcement Logic:**
1. DIO calculates data age: `age = current_date - as_of_date`
2. Compare against both thresholds
3. If `age > hard_stop_threshold` → DIO VETO (holding or portfolio level, depending on data type)
4. Else if `age > penalty_threshold` → Suggest penalty to Risk Officer (Category B)
5. Else → No penalty

**Invariant**: Data that triggers hard-stop does NOT also trigger penalty. Hard-stop supersedes penalty.

### 7.4 Penalty Calculation Rules (R17 — Updated with Category F)

#### Category A: Missing Critical Data (0 to -20, capped)

Missing PenaltyCriticalFieldRegistry fields:

* Missing `cash` or `runway` (for non-burn-rate company where not N/A): **-6**
* Missing `shares_outstanding` or `market_cap`: **-5**
* Missing `fully_diluted_shares`: **-4**
* Missing `adv_usd` or liquidity measure: **-5**
* Missing `price` or `volume`: **-4**
* Missing macro regime input (e.g., `vix`): **-4**

**Cap**: -20 total for Category A

#### Category B: Staleness Penalties (0 to -10, capped)

Data age beyond penalty threshold but within hard-stop:

* **Financials** stale:
  * DEEP mode: >90 days, ≤180 days → **-5**
  * FAST mode: >120 days, ≤365 days → **-5**
* **Price/Volume** stale:
  * DEEP mode: >1 day, ≤14 days → **-3**
  * FAST mode: >3 days, ≤30 days → **-3**
* **Company Updates** stale:
  * DEEP mode: >60 days → **-2**
  * FAST mode: >90 days → **-2**
* **Macro/Regime** stale:
  * DEEP mode: >7 days, ≤30 days → **-4**
  * FAST mode: >14 days, ≤90 days → **-4**

**Cap**: -10 total for Category B

**Note**: Data beyond hard-stop threshold does NOT trigger penalties — it triggers DIO VETO instead.

#### Category C: Contradictions / Integrity Issues (0 to -20, capped)

* DIO detects contradiction in critical metrics (e.g., conflicting market cap from two sources): **-10**
* Conflicting sources unresolved: **-6**
* Unsourced numbers detected in agent output: **-10** AND trigger DIO veto flag

**Cap**: -20 total for Category C

#### Category D: Confidence Penalties (0 to -10, capped)

* Multiple agents (≥3) report confidence <0.5: **-5**
* Devil's Advocate raises unresolved fatal risk: **-5**

**Cap**: -10 total for Category D

#### Category E: FX Exposure Risk (0 to -10, capped)

* FX rate missing when instrument.currency ≠ base_currency: **-5**
* FX rate stale beyond penalty threshold (but within hard-stop): **-3**
* High FX exposure (>20% portfolio) without hedging data: **-5**

**Cap**: -10 total for Category E

**Note**: FX rate beyond hard-stop threshold triggers DIO VETO, not penalty.

#### Category F: Data Validity (0 to -10, capped) — NEW (R17)

Corporate actions and data quality issues that affect metric validity:

* Recent stock split/reverse split detected (within 90 days): **-6**
* Recent dividend/distribution affecting price comparisons: **-3**
* Recent spinoff/merger affecting structure: **-8**
* Data source reliability flagged as low: **-5**

**Cap**: -10 total for Category F

**CRITICAL DISTINCTION**: 
* Corporate actions go to Category F (Data Validity), NOT Category B (Staleness)
* Staleness = age of data
* Data validity = structural changes affecting metric comparability

#### Total Penalty Cap

* **DEEP mode**: -35 (sum of all categories, enforced)
* **FAST mode**: -40 (slightly more lenient)

#### Penalty Enforcement Process

1. Risk Officer calculates penalties per category
2. Apply individual category caps first (A: -20, B: -10, C: -20, D: -10, E: -10, F: -10)
3. Sum all categories
4. Apply total cap (-35 DEEP or -40 FAST)
5. If total penalties approach cap AND high uncertainty → Risk Officer may trigger veto

### 7.5 Recommendation Category Mapping (After Penalties)

Based on FinalScore = clamp(BaseScore - TotalPenalties, 0, 100):

* **80–100**: **Buy/Increase** (subject to LEFO liquidity caps, PSCC concentration caps, GRRA regime constraints)
* **65–79**: **Watch / Accumulate Cautiously**
* **50–64**: **Watchlist Only** (no add unless conditions improve)
* **0–49**: **Avoid / Reduce**

#### Hard Override Rules (Precedence — ABSOLUTE):

Apply in strict order:

1. **DIO VETOED** → "Insufficient data / integrity failure" (no recommendation)
2. **GRRA SHORT_CIRCUITED** → "No new positions allowed" (regime constraint)
3. **LEFO liquidity_grade ≤1** → **Avoid** OR position capped to <1% (regardless of score)
4. **PSCC concentration breach** → Position capped or downgraded to **Watch**
5. **Risk Officer extreme uncertainty** → **VETOED**

**Invariant**: Lower-numbered overrides supersede higher-numbered ones.

### 7.6 Unknown vs Not Applicable Semantics (R3, RISK-S6)

**Unknown** (`value = None, missing_reason = "data unavailable"`):
* Represents missing data that SHOULD exist for this instrument type
* Triggers penalties (Category A if critical, Category D if confidence-related)
* Must be explicitly handled; never silently treated as zero
* Example: Missing `cash` for a startup where `is_burn_rate_company = true`

**Not Applicable** (`not_applicable = true`):
* Field is irrelevant for this instrument type/sector
* Does NOT trigger penalties
* Should be used for sector/type mismatches
* Example: `burn_rate` for a bank (banks don't have burn rates)

**Enforcement**: 
* DIO validates semantic correctness
* If `not_applicable = true` but field is actually critical for this instrument type → DIO flags contradiction (Category C penalty)
* Scoring rubric may have sector-specific weights in v1.0+

**Schema Rules**:
* If `value = None` AND `not_applicable = false` AND `missing_reason = None` → SCHEMA VIOLATION → FAILED
* If `not_applicable = true` → `value` SHOULD be None, `missing_reason` SHOULD be empty

### 7.7 FX Exposure Handling (R11)

**Trigger**: If `instrument.currency != portfolio.base_currency`

**Actions**:
1. Risk Officer flags FX exposure
2. Check FX rate availability:
   * If FX rate missing → Category E penalty (-5)
   * If FX rate stale beyond hard-stop → DIO VETO (portfolio-level)
   * If FX rate stale beyond penalty threshold but within hard-stop → Category E penalty (-3)
3. PSCC aggregates FX exposure across holdings
4. Position sizing guidance includes FX exposure note
5. If FX exposure >20% portfolio without hedging data → Category E penalty (-5)

**Disclaimers**:
* If FX rate present but low confidence → include warning in disclaimers
* Always note currency exposure in position_sizing_guidance.fx_exposure_note

---

## §8) Testing Strategy (DESIGN ONLY — NO IMPLEMENTATION)

### 8.1 Schema Validation Tests

**Objective**: Ensure all schemas validate correctly and reject invalid inputs.

**Test Cases**:
* Valid InstrumentIdentity (ticker, exchange, currency present) → PASS
* Missing required field (e.g., currency) → FAIL
* Invalid enum value (e.g., regime_label = "PANIC") → FAIL
* MetricValue with value but missing SourceRef → FAIL
* AgentResult with confidence >1.0 → FAIL
* RunConfig with both is_burn_rate_company = true AND not_applicable = true → FAIL (schema violation)

**Coverage**: All 25+ schemas defined in §5

### 8.2 Integration Tests (End-to-End Portfolio Runs)

#### Test Case I1: Happy Path (DEEP mode, N=3 holdings, all complete)

* **Inputs**: Valid PortfolioSnapshot (3 equities), complete seeded data, RunConfig (DEEP, burn_rate_classification provided)
* **Expected Outputs**:
  * portfolio_run_outcome = COMPLETED
  * All 3 holdings: holding_run_outcome = COMPLETED
  * All scorecards valid, penalties applied, recommendations assigned
  * PortfolioCommitteePacket + 3 HoldingPackets emitted
  * canonical_output_hash matches on re-run with same inputs

#### Test Case I2: DIO Portfolio Veto (Missing base_currency)

* **Inputs**: PortfolioSnapshot provided, base_currency missing in PortfolioConfig
* **Expected Outputs**:
  * portfolio_run_outcome = VETOED
  * Error message: "base_currency required when portfolio provided"
  * Minimal PortfolioCommitteePacket with veto note
  * RunLog includes DIO veto event
  * No canonical_output_hash

#### Test Case I3: GRRA Short-Circuit (CRISIS regime)

* **Inputs**: Valid portfolio, GRRA outputs regime_label = CRISIS, do_not_trade = true
* **Expected Outputs**:
  * portfolio_run_outcome = SHORT_CIRCUITED
  * All holdings: holding_run_outcome = SHORT_CIRCUITED
  * PortfolioCommitteePacket includes regime constraint note
  * HoldingPackets include SHORT_CIRCUITED status, no recommendations
  * No canonical_output_hash

#### Test Case I4: Partial Failure (1 of 3 holdings vetoed)

* **Inputs**: Valid portfolio (3 holdings), holding #2 missing cash field and is_burn_rate_company = true
* **Expected Outputs**:
  * portfolio_run_outcome = COMPLETED (only 33% vetoed, <30% threshold)
  * Holding #1: COMPLETED
  * Holding #2: VETOED (missing HardStopField)
  * Holding #3: COMPLETED
  * per_holding_outcomes explicitly lists all 3 outcomes
  * canonical_output_hash generated

#### Test Case I5: Excessive Failures (2 of 3 holdings vetoed)

* **Inputs**: Valid portfolio, holdings #1 and #2 both missing critical hard-stop data
* **Expected Outputs**:
  * portfolio_run_outcome = VETOED (67% vetoed, >30% threshold)
  * Holding #1: VETOED
  * Holding #2: VETOED
  * Holding #3: COMPLETED
  * PortfolioCommitteePacket includes limitation note
  * No canonical_output_hash

#### Test Case I6: Runtime Exception (Orchestrator FAILED)

* **Inputs**: Valid portfolio, but RunConfig has malformed JSON
* **Expected Outputs**:
  * portfolio_run_outcome = FAILED
  * FailedRunPacket emitted with error details
  * RunLog includes error traceback
  * No PortfolioCommitteePacket or HoldingPackets
  * No canonical_output_hash

#### Test Case I7: Agent Exception During Holding Evaluation

* **Inputs**: Valid portfolio, Fundamentals Agent crashes on holding #2
* **Expected Outputs**:
  * portfolio_run_outcome = COMPLETED (if <30% fail)
  * Holding #1: COMPLETED
  * Holding #2: FAILED (agent exception)
  * Holding #3: COMPLETED
  * RunLog includes error for holding #2
  * HoldingPacket omitted for holding #2 (or minimal with FAILED status)

#### Test Case I8: Identity Validation (FAILED not VETOED)

* **Inputs**: Portfolio with holding missing ticker field (schema violation)
* **Expected Outputs**:
  * holding_run_outcome = FAILED (not VETOED — schema violation = technical failure)
  * Other holdings continue
  * RunLog includes error
  * Error message indicates schema validation failure

#### Test Case I9: Burn-Rate Classification Logic

* **Inputs**: Portfolio with 3 holdings (DEEP mode):
  * Holding A: is_burn_rate_company = true, missing cash → VETOED
  * Holding B: is_burn_rate_company = false, missing cash → penalty only
  * Holding C: not_applicable = true, missing cash → no penalty
* **Expected Outputs**:
  * Holding A: VETOED (cash in HardStopFieldRegistry)
  * Holding B: COMPLETED with Category A penalty (-6)
  * Holding C: COMPLETED with no penalty (cash ignored)

#### Test Case I10: Staleness Dual Thresholds

* **Inputs**: Portfolio with 2 holdings (DEEP mode):
  * Holding A: financials 100 days old (>90d penalty, <180d hard-stop)
  * Holding B: financials 200 days old (>180d hard-stop)
* **Expected Outputs**:
  * Holding A: COMPLETED with Category B penalty (-5)
  * Holding B: VETOED (staleness hard-stop triggered)

#### Test Case I11: Corporate Action Category F

* **Inputs**: Valid portfolio, holding #1 has recent stock split (60 days ago)
* **Expected Outputs**:
  * DIO flags corporate_action_risk
  * Category F penalty applied: -6 (NOT Category B)
  * Penalty breakdown shows Category F entry
  * FinalScore reduced accordingly

#### Test Case I12: Reproducibility (Canonical Hash)

* **Inputs**: Same portfolio + config + data, run twice with different retrieval_timestamp
* **Expected Outputs**:
  * canonical_output_hash IDENTICAL on both runs
  * input_snapshot_hash DIFFERENT (includes retrieval_timestamp)
  * run_id DIFFERENT (excluded from canonical hash)
  * All decision fields (scores, penalties, recommendations) IDENTICAL

#### Test Case I13: Veto Precedence

* **Inputs**: Holding with:
  * DIO veto (missing ticker) AND
  * GRRA short-circuit (crisis regime)
* **Expected Outputs**:
  * holding_run_outcome = VETOED (DIO precedence over GRRA)
  * Veto note indicates DIO hard-stop
  * GRRA constraint noted but DIO takes precedence

#### Test Case I14: Override Precedence

* **Inputs**: Holding with:
  * High score (85) AND
  * LEFO liquidity_grade = 0 AND
  * PSCC concentration breach
* **Expected Outputs**:
  * holding_run_outcome = COMPLETED
  * recommendation_category = "Avoid" (LEFO override supersedes score)
  * position_sizing_guidance.max_weight_pct = 0.0 or <1% (LEFO)
  * PSCC cap also noted but LEFO takes precedence

### 8.3 Penalty Logic Tests

**Objective**: Validate deterministic penalty calculations.

**Test Cases**:
* Missing 3 PenaltyCriticalFieldRegistry fields → Category A penalty = -15 (within -20 cap)
* Stale financials (100 days, DEEP penalty threshold 90d) → Category B penalty = -5
* Contradiction detected → Category C penalty = -10
* Devil's Advocate raises fatal risk → Category D penalty = -5
* Corporate action (split 60d ago) → Category F penalty = -6 (NOT Category B)
* Total penalties = -42 → capped at -35 (DEEP mode)

### 8.4 Canonicalization Tests

**Objective**: Validate reproducibility.

**Test Cases**:
* Holdings in different order → canonical_output_hash IDENTICAL
* Different run_id → canonical_output_hash IDENTICAL
* Different retrieval_timestamp → canonical_output_hash IDENTICAL
* Different narrative notes → canonical_output_hash IDENTICAL
* Different as_of_date → canonical_output_hash DIFFERENT

### 8.5 Error Resilience Tests

**Objective**: Ensure system fails gracefully.

**Test Cases**:
* Malformed JSON input → portfolio_run_outcome = FAILED, FailedRunPacket emitted
* Missing InstrumentIdentity → holding FAILED, others continue
* Exception in Fundamentals Agent → holding FAILED, others continue
* All agents fail for a holding → holding FAILED, portfolio completes if <30% fail
* Orchestrator exception in Phase 3 → portfolio FAILED, FailedRunPacket emitted

---

## §9) Phased Delivery Plan

### Phase v0.1: MVP — Manual Inputs + Schema-Valid Packets

**Scope**:

* Portfolio-first orchestration (N≥1 holdings)
* All 10 agents implemented (Chair, DIO, GRRA, Data Ingestion, Fundamentals, Technical, LEFO, PSCC, Risk Officer, Devil's Advocate)
* Manual/seeded data inputs (paste financials, upload CSV/JSON)
* All schemas defined and validated
* Scoring rubric with 8 dimensions + 6 penalty categories (A, B, C, D, E, F)
* Veto gates + override hierarchy enforced
* Deterministic orchestration, FAST/DEEP modes
* RunLog with full audit trail
* FailedRunPacket for runtime exceptions
* Canonical hash for reproducibility
* Dual staleness thresholds (penalty + hard-stop)
* HardStopFieldRegistry vs PenaltyCriticalFieldRegistry split
* Burn-rate classification conditional logic
* Corporate action risk as Category F (Data Validity)
* Unit tests + integration tests (design implemented)

**Deliverables**:

* Working Python package (orchestrator + schemas)
* Test suite (pytest)
* Sample portfolios (6 test cases: happy path, veto, short-circuit, failed, partial failure, burn-rate conditional)
* Documentation (schema reference, rubric guide, veto rules, outcome semantics, canonicalization rules)

**Acceptance Criteria**:

* All R1–R20 requirements met
* All integration test cases (I1–I14) pass
* Schema validation tests pass
* Reproducibility tests pass (canonical hash)
* Outcome semantics correctly enforced (FAILED vs VETOED vs SHORT_CIRCUITED)
* Registry split correctly implemented
* Burn-rate classification logic correct

### Phase v0.2: Portfolio-Aware Enhancements + FX Normalization

**Scope**:

* FX normalization pipeline (base_currency conversions)
* Enhanced PSCC correlation estimation (optional, manual inputs)
* Sector-specific rubrics (different weights for banks vs tech)
* `not_applicable` semantic handling per sector
* Historical run comparison utilities
* Expanded test coverage (20+ integration tests)

**Deliverables**:

* FX engine with timestamp validation
* Sector rubric registry
* Run comparison CLI tool
* Updated documentation

### Phase v1.0: Production-Grade + Monitoring

**Scope**:

* Automated data ingestion (optional APIs, still validate provenance)
* Corporate action adjustment pipeline
* Symbol mapping / ISIN resolution
* Enhanced DIO contradiction resolution workflow
* Memory/retrieval system for historical context
* Monitoring dashboard (run outcomes, veto rates, penalty distributions)
* Retention + archival policy enforcement
* Performance benchmarking vs indices

**Deliverables**:

* Data ingestion adapters (Yahoo Finance, manual API keys)
* Corporate action engine
* Monitoring UI (Streamlit or similar)
* Historical run database (SQLite or similar)
* Performance analytics module

### Phase v2.0+: Advanced Features (Future)

* Multi-asset support (bonds, options, crypto)
* Dynamic agent spawning for specialized analysis
* LLM-powered agents (with strict DIO validation)
* Real-time alerting for regime changes
* Portfolio optimization suggestions
* Tax-aware position sizing
* Compliance automation (restricted lists, blackout periods)

---

## §10) Open Clarifications

The following items require stakeholder decision before finalizing implementation (design can proceed with proposed defaults):

### C-1: Exact Liquidity Grade Thresholds (C4)

**Question**: Should liquidity_grade thresholds be based on absolute ADV in USD, or relative to position size?

**Options**:
* **Option A**: Fixed ADV thresholds (e.g., grade 0 = <$10K ADV, grade 5 = >$10M ADV)
* **Option B**: Relative to position size (e.g., grade 3 = "can exit position in <2 days without >2% slippage")

**Recommendation**: Option B (relative) is more robust but requires position size assumptions. Option A is simpler for MVP.

**Impact**: LEFO logic and test cases.

---

### C-2: Partial Failure Threshold (C7, R20)

**Question**: Should the 30% threshold for portfolio-level VETOED be configurable per user, or hardcoded?

**Options**:
* **Option A**: Hardcoded 30% (simpler, deterministic)
* **Option B**: Configurable in PortfolioConfig.failure_tolerance_pct

**Recommendation**: Hardcoded for v0.1, configurable in v0.2.

**Impact**: Orchestration logic and user experience.

---

### C-3: Correlation Matrix Source (M4)

**Question**: In MVP, should correlation matrix be:
* **Option A**: Purely manual input (user provides), optional
* **Option B**: Computed from provided price history (if available)
* **Option C**: Not supported in v0.1

**Recommendation**: Option A (manual, optional) to avoid complexity. Add computation in v0.2 if price history is available.

**Impact**: PSCC logic and test data requirements.

---

### C-4: Devil's Advocate Veto Authority

**Question**: Should Devil's Advocate ever have veto power, or always advisory?

**Options**:
* **Option A**: Always advisory (current design)
* **Option B**: Can veto if raises "unresolved fatal risk" and other agents have low confidence

**Recommendation**: Option A for v0.1 (simpler governance). Reassess in v0.2 if counter-case signals correlate with outsized drawdowns.

**Impact**: Governance complexity and override precedence rules.
