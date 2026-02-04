# DD-02 — DATA_CONTRACTS.md

## 1. Purpose
Define the **data exchange contracts** between system components and agents in a portfolio-first execution model.

This document specifies:
- Which schemas are exchanged
- At what scope (portfolio-level vs holding-level)
- Required vs optional payloads
- Contractual guarantees between producers and consumers

This document does NOT define:
- Execution logic
- Validation logic
- Penalty logic
- Orchestration sequencing

---

## 2. Contract Scope Definitions

### Portfolio-Level Contracts
- Apply once per run.
- Represent aggregate or global context.
- Must be internally consistent across all holdings.

### Holding-Level Contracts
- Apply independently per holding.
- May succeed or fail independently.
- Must not implicitly affect other holdings unless explicitly stated.

### Embedded Contracts
- Used only within other schemas.
- Never transmitted independently.
- In scope: **InstrumentIdentity**, **SourceRef**, **MetricValue** (per DD-01).  

---

## 3. Core Contract Participants

### Orchestrator
- **Receives:** PortfolioSnapshot, PortfolioConfig, RunConfig, and holding-level inputs.  
- **Must produce:** PortfolioCommitteePacket (or FailedRunPacket when applicable) and RunLog.  
- **Must not produce or mutate:** Agent-specific outputs (e.g., DIOOutput, GRRAOutput, LEFOOutput, PSCCOutput, Fundamentals/Technical/Liquidity outputs) beyond embedding them in portfolio-level packets.  

### Data Ingestion Layer
- **Receives:** Raw portfolio/holding data required to form PortfolioSnapshot, PortfolioConfig, RunConfig, and InstrumentIdentity.  
- **Must produce:** PortfolioSnapshot, PortfolioConfig, RunConfig, and holding-level inputs with InstrumentIdentity.  
- **Must not produce or mutate:** AgentResult-derived outputs, Scorecard, or any portfolio/holding outcomes.  

### DIO (Data Integrity Officer)
- **Receives:** Holding-level inputs (including InstrumentIdentity), MetricValue-bearing data, and applicable configuration snapshots.  
- **Must produce:** DIOOutput.  
- **Must not produce or mutate:** Other agents’ outputs, Scorecard, or portfolio-level outputs.  

### Analytical Agents (Fundamentals, Technical, Liquidity, etc.)
- **Receives:** Holding-level inputs, InstrumentIdentity, and MetricValue-bearing data; may also receive portfolio context where required by schema.  
- **Must produce:** AgentResult-based outputs scoped to their schemas (e.g., Fundamentals Agent Output, Technical Agent Output, Liquidity/PSCC Agent Output).  
- **Must not produce or mutate:** DIOOutput, GRRAOutput, Risk Officer Output, or portfolio-level packets.  

### Risk Officer
- **Receives:** PortfolioSnapshot, portfolio-level outputs (GRRAOutput, PSCCOutput), holding-level outputs, and Scorecard/PenaltyBreakdown as defined by schemas.  
- **Must produce:** Risk Officer Output (AgentResult-based).  
- **Must not produce or mutate:** PortfolioSnapshot, PortfolioConfig, RunConfig, or other agents’ outputs.  

### Chair / Aggregator
- **Receives:** PortfolioSnapshot, PortfolioConfig, RunConfig, GRRAOutput, PSCCOutput, holding-level outputs, and Scorecard(s).  
- **Must produce:** PortfolioCommitteePacket and HoldingPacket(s).  
- **Must not produce or mutate:** Upstream agent outputs or any schema fields not defined in HLD §5.  

**DESIGN DECISION:** The precise routing of inputs between Orchestrator and Chair/Aggregator is not fully specified in HLD §5. The contract boundary here treats the Chair/Aggregator as the producer of PortfolioCommitteePacket and HoldingPacket(s), with the Orchestrator responsible for ensuring those packets are emitted per §5 schemas. This preserves schema responsibilities without implying sequencing.  

---

## 4. Primary Data Contracts

### 4.1 PortfolioSnapshot Contract
- **Producer:** Data Ingestion Layer.  
- **Consumers:** Orchestrator, Chair/Aggregator, Risk Officer, portfolio-level agents as applicable.  
- **Required fields:** `snapshot_date`, `holdings`, `cash_pct`.  
- **Optional fields:** `total_value_base_currency`.  
- **Scope:** Portfolio-level.  
- **Immutability guarantees:** PortfolioSnapshot is treated as read-only once emitted; consumers must not mutate holdings or weights.  

### 4.2 PortfolioConfig Contract
- **Producer:** Data Ingestion Layer.  
- **Consumers:** Orchestrator, Chair/Aggregator, Risk Officer, PSCC.  
- **Required fields:** `base_currency` (required if PortfolioSnapshot provided), `risk_tolerance`, `concentration_limits`.  
- **Optional fields:** `theme_tags`, `compliance_flags`.  
- **Failure semantics if missing:** Missing `base_currency` when PortfolioSnapshot is provided constitutes a HardStop field omission at the portfolio level and is therefore a VETO-eligible contract failure.  

### 4.3 Holding Input Contract
- **How InstrumentIdentity is supplied:** As the `instrument` field within each Holding in PortfolioSnapshot; InstrumentIdentity is a required embedded schema for holding-level inputs.  
- **Holding-level isolation rules:** Each holding is evaluated independently; holding-level outputs must reference their own `holding_id` and `instrument` without dependency on other holdings.  
- **Identity completeness guarantees:** `ticker`, `exchange`, and `currency` are required for every holding; missing any of these fields constitutes a technical failure (holding_run_outcome=FAILED) per the Outcome Classification Rule below.  

### 4.4 RunConfig Contract
- **Producer:** Data Ingestion Layer.  
- **Consumers:** Orchestrator, Chair/Aggregator, guards, and governance layers.  
- **Required fields:** `run_mode` and any thresholds or caps referenced by guards (e.g., penalty caps, staleness thresholds, `partial_failure_veto_threshold_pct`).  
- **Optional fields:** `debug_mode` (boolean).  
- **Semantics:** `debug_mode` enables diagnostic logging of guard violations but MUST NOT alter outcomes or emission eligibility.  
- **Immutability guarantees:** RunConfig is treated as read-only once emitted.  

### 4.5 ConfigSnapshot Contract
- **Producer:** Data Ingestion Layer or governance configuration service.  
- **Consumers:** DIO, Penalty Engine, Orchestrator, Chair/Aggregator.  
- **Required fields:** `hard_stop_field_registry`, `penalty_critical_field_registry`, `scoring_rubric_version`, `agent_prompt_versions`.  
- **Optional fields:** None (schema is fixed per DD-01).  
- **Scope:** Portfolio-level.  
- **Immutability guarantees:** ConfigSnapshot is read-only once emitted.  

---

## 5. Agent Output Contracts

### Common AgentResult Contract
- **Schema authority:** AgentResult fields are defined in DD-01; the list below is a contract summary and must match DD-01.  
- **Required fields:** `agent_name`, `status`, `confidence`, `key_findings`, `metrics`, `suggested_penalties`, `veto_flags`.  
- **Optional fields:** `counter_case`, `notes`.  
- **Use of MetricValue:** All metric entries must be MetricValue objects; when `value` is present, `source_ref` is required.  
- **Provenance guarantees:** MetricValue enforces provenance via SourceRef when a value is present; missing provenance is a contract violation. MetricValue.SourceRef is the single authoritative provenance structure.  
- **Prohibited behaviors:** Agents must not introduce fields outside the schema or populate MetricValue.value without an accompanying SourceRef.  

### Agent-Specific Output Constraints

#### DIOOutput
- **Contract:** Extends AgentResult with data integrity fields (`data_confidence`, `staleness_flags`, `missing_hard_stop_fields`, `missing_penalty_critical_fields`, `contradictions`, `corporate_action_risk`, `unsourced_numbers_detected`, `integrity_veto_triggered`).  
- **Advisory fields:** `staleness_flags`, `missing_penalty_critical_fields`, `contradictions`, `corporate_action_risk`.  
- **Potential veto/short-circuit fields:** `missing_hard_stop_fields`, `integrity_veto_triggered`, `unsourced_numbers_detected` (as indicators only; logic not defined here).  

#### GRRAOutput
- **Contract:** Extends AgentResult with regime fields (`regime_label`, `regime_confidence`, `risk_budget_multiplier`, `required_checks`, `do_not_trade_flag`, `regime_indicators`).  
- **Advisory fields:** `risk_budget_multiplier`, `required_checks`, `regime_indicators`.  
- **Potential veto/short-circuit fields:** `do_not_trade_flag` (indicator only; logic not defined here).  

#### Fundamentals Agent Output
- **Contract:** AgentResult with `metrics` populated by fundamentals MetricValue entries (e.g., revenue, earnings, market_cap) as listed in PenaltyCriticalFieldRegistry.  
- **Advisory fields:** `key_findings`, `metrics`, `suggested_penalties`.  
- **Potential veto/short-circuit fields:** `veto_flags` (indicator only).  

#### Technical Agent Output
- **Contract:** AgentResult with `metrics` populated by technical MetricValue entries (e.g., price, volume, 52w_high, 52w_low, beta) as listed in PenaltyCriticalFieldRegistry.  
- **Advisory fields:** `key_findings`, `metrics`, `suggested_penalties`.  
- **Potential veto/short-circuit fields:** `veto_flags` (indicator only).  

#### Liquidity / PSCC Agent Output
- **Contract:**  
  - Holding-level liquidity follows LEFOOutput (liquidity_grade, adv_usd, bid_ask_spread_bps, time_to_exit_estimate, max_position_cap_pct, exit_risk_warnings, hard_override_triggered).  
  - Portfolio-level concentration follows PSCCOutput (concentration_by_name/sector/theme, fx_exposure_by_currency, correlation_matrix, concentration_breaches, position_caps_applied, portfolio_liquidity_risk).  
- **Advisory fields:** `exit_risk_warnings`, `portfolio_liquidity_risk`, `concentration_breaches`.  
- **Potential veto/short-circuit fields:** `hard_override_triggered` (indicator only).  

#### Risk Officer Output
- **Contract:** AgentResult-based output with risk-related `key_findings`, `metrics`, `suggested_penalties`, and `veto_flags` per schema.  
- **Advisory fields:** `key_findings`, `metrics`, `suggested_penalties`.  
- **Potential veto/short-circuit fields:** `veto_flags` (indicator only).  

---

## 6. Portfolio vs Holding Contract Interaction Rules

- If a holding fails, its HoldingPacket must still include `holding_id`, `instrument`, and `holding_run_outcome`, plus `limitations` containing an error classification entry derived from RunLog.ErrorRecord.error_type; omit `scorecard`, `recommendation_category`, and `position_sizing_guidance` per schema rules.  
- If multiple holdings fail, `per_holding_outcomes` in the PortfolioCommitteePacket must still enumerate all holding outcomes.  
- Portfolio-level aggregation data (`pscc_output`, `portfolio_level_metrics`, `canonical_output_hash`) is only present when `portfolio_run_outcome = COMPLETED`.  
- Holding-level failures do not remove the holding from `portfolio_snapshot` or `holdings` lists; they only constrain which fields appear in each HoldingPacket.  

**DESIGN DECISION:** HLD §5 defines when portfolio-level outputs are present based on `portfolio_run_outcome`, but it does not explicitly state whether holding-level failures preclude portfolio-level aggregation. This document follows the schema rules: portfolio-level aggregation appears only when `portfolio_run_outcome = COMPLETED`, regardless of individual holding failures.  

---

## 7. Contract Failure Semantics (DESIGN-LEVEL)

### Contract Violations
At the contract boundary, a violation is any instance where required fields are missing, types are malformed, or semantic rules in embedded schemas are broken.

### Violation Types
- **Missing contract:** Required schema payload is absent (e.g., PortfolioSnapshot not provided when a portfolio run is requested).  
- **Malformed contract:** Required fields are present but malformed or unparseable (e.g., datetime not tz-aware UTC where required).  
- **Semantically invalid contract:** Violates embedded semantic rules (e.g., MetricValue has `value = null`, `not_applicable = false`, and `missing_reason = null`).  

### Eligibility Mapping (No Enforcement Logic)
- **FAILED eligibility:** Malformed or semantically invalid contracts that prevent trustworthy interpretation of required fields, including missing holding identity fields (`ticker`, `exchange`, `currency`).  
- **VETOED eligibility:** Missing portfolio-level hard-stop fields (`base_currency` when required) as defined by HardStopFieldRegistry.  

### Outcome Classification Rule (Authoritative)
Outcome classification for identity and base-currency omissions is defined as follows and must be referenced by guards and orchestration flow documents to avoid drift:

- **Holding identity omissions** (`ticker`, `exchange`, or `currency` missing) are **technical failures** ⇒ `holding_run_outcome=FAILED`.
- **Portfolio base_currency omission** when PortfolioSnapshot is present is a **governance veto** ⇒ `portfolio_run_outcome=VETOED`.

**DESIGN DECISION:** HLD §5 identifies hard-stop identity and base_currency omissions as veto conditions, but does not explicitly map technical identity omissions versus governance vetoes. This document treats holding identity omissions as FAILED (technical) while retaining portfolio base_currency omission as VETOED, and assigns other malformed/semantic violations to FAILED to preserve schema integrity without defining enforcement behavior.  

---

## 8. Traceability

| Section | HLD v1.0 §5 Reference | DD-01 Schema References |
|---|---|---|
| 2. Contract Scope Definitions | §5.1 Core Schemas (InstrumentIdentity, SourceRef, MetricValue) | InstrumentIdentity, SourceRef, MetricValue |
| 3. Core Contract Participants | §5.1 Core Schemas; §5 HoldingPacket; §5 PortfolioCommitteePacket; §5 RunLog | InstrumentIdentity, SourceRef, MetricValue |
| 4. Primary Data Contracts | §5 PortfolioSnapshot; §5 PortfolioConfig; §5 Holding (embedded in PortfolioSnapshot) | InstrumentIdentity |
| 5. Agent Output Contracts | §5 AgentResult; §5 DIOOutput; §5 GRRAOutput; §5 LEFOOutput; §5 PSCCOutput | MetricValue, SourceRef |
| 6. Portfolio vs Holding Interaction Rules | §5 HoldingPacket; §5 PortfolioCommitteePacket | InstrumentIdentity |
| 7. Contract Failure Semantics | §5 MetricValue semantic rules; §5 HardStopFieldRegistry | MetricValue |

---

## 9. Non-Goals

This document does NOT cover:
- Orchestration sequencing or state transitions.
- Validation or penalty algorithms.
- Scoring logic or risk logic.
- Any implementation, storage, or API details.
- Any schema fields not explicitly defined in HLD v1.0 §5 or DD-01.

---

STATUS: DD-02 COMPLETE — Awaiting transition to DD-04 (ORCHESTRATION_FLOW.md)
