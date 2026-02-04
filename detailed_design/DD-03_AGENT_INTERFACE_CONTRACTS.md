# DD-03 — Agent Interface Contracts (Portfolio-First)

## 1. Purpose
This document defines the **formal input/output contracts** for every agent in the system. Agents emit **structured signals only**; they do **not** make governance decisions or enforcement actions.

Invariants:
- Agents **never** issue final scores.
- Agents **never** apply penalties.
- Agents **never** override governance precedence.
- Outputs are deterministic, auditable, and portfolio-first.

---

## 2. Agent Interface Standard (MANDATORY)
All agents MUST emit the common **AgentResult** envelope. This wrapper is required for every agent, every scope, and every execution outcome.

### 2.1 AgentResult Envelope (Required Fields)
- **agent_name**
- **status**: `completed` | `failed` | `skipped`
- **confidence**: 0.0–1.0
- **key_findings**: agent-specific structured findings
- **metrics**: list of MetricValue entries
- **suggested_penalties**: list of PenaltyItem entries
- **veto_flags**: advisory-only flags (if applicable)
- **counter_case** (optional; Devil’s Advocate only)
- **notes** (optional)

### 2.2 Envelope Invariants
- Agents **never emit final scores**.
- Agents **never apply penalties**.
- Agents **never override governance** (veto/short-circuit/caps are enforced elsewhere).
- Any numeric value in `key_findings` or `metrics` requires traceable provenance via **MetricValue.SourceRef**.
- Provenance validation is based solely on MetricValue.SourceRef.

---

## 3. Per-Agent Interface Definitions
Each agent below MUST conform to the AgentResult envelope and provide the explicit inputs/outputs listed. All outputs are **signals only** and become enforceable only through governance layers.

### 3.A Fundamentals Agent (Holding-Scoped)
**Inputs**
- HoldingSnapshot
- Seeded financial data (sourced MetricValue inputs)

**Outputs (within AgentResult.key_findings + metrics)**
- `fundamental_metrics` (structured findings)
- MetricValue entries for fundamentals metrics

### 3.B Technical Agent (Holding-Scoped)
**Inputs**
- Price/volume time series (sourced)

**Outputs (within AgentResult.key_findings + metrics)**
- `technical_signals` (structured findings)
- MetricValue entries for technical metrics

### 3.C Macro / Regime Inputs (Portfolio-Scoped)
**Inputs**
- Portfolio-level macro/regime indicators (sourced)

**Outputs (within AgentResult.key_findings + metrics)**
- `regime_indicators` (signals only; no policy decisions)
- MetricValue entries for regime indicators

### 3.D Devil’s Advocate (Holding-Scoped)
**Inputs**
- HoldingSnapshot
- All prior analytical outputs (read-only)

**Outputs (within AgentResult.key_findings)**
- `risk_flags`
- `unresolved_fatal_risk` (boolean)
- `narrative_limitations`

### 3.E Data Integrity Officer (DIO) (Holding-Scoped + Portfolio-Scoped)
**Inputs**
- HoldingSnapshot and PortfolioSnapshot
- All MetricValue-bearing inputs and SourceRefs
- Registry snapshots (hard-stop vs penalty-critical)

**Outputs (AgentResult + DIOOutput fields)**
- `missing_hard_stop_fields`
- `missing_penalty_critical_fields`
- `staleness_flags`
- `contradictions`
- `unsourced_numbers_detected`
- `corporate_action_risk`

### 3.F Global Risk Regime Architect (GRRA) (Portfolio-Scoped)
**Inputs**
- PortfolioSnapshot
- Regime indicators (sourced)

**Outputs (AgentResult + GRRAOutput fields)**
- `regime_label`
- `regime_confidence`
- `do_not_trade_flag`

### 3.G Liquidity & Exit Feasibility Officer (LEFO) (Holding-Scoped)
**Inputs**
- HoldingSnapshot
- Liquidity and spread inputs (sourced)

**Outputs (AgentResult + LEFOOutput fields)**
- `liquidity_grade`
- `hard_override_flags`

### 3.H Portfolio Structure & Concentration Controller (PSCC) (Portfolio-Scoped)
**Inputs**
- PortfolioSnapshot
- Holding-level outputs (read-only)
- PortfolioConfig

**Outputs (AgentResult + PSCCOutput fields)**
- `concentration_breaches`
- `fx_exposure_flags`

---

## 4. Scope Rules

### 4.1 Holding-Scoped Agents
- Fundamentals Agent
- Technical Agent
- Devil’s Advocate
- Data Integrity Officer (holding-level checks)
- Liquidity & Exit Feasibility Officer (LEFO)

### 4.2 Portfolio-Scoped Agents
- Global Risk Regime Architect (GRRA)
- Portfolio Structure & Concentration Controller (PSCC)
- Data Integrity Officer (portfolio-level checks)
- Macro / Regime Inputs

### 4.3 Governance-Authoritative vs Advisory
- **Governance-authoritative (signals consumed by governance rules):** DIO, GRRA, LEFO, PSCC.
- **Advisory-only:** Fundamentals, Technical, Devil’s Advocate, Macro/Regime Inputs.
- **Chair** consumes all outputs and aggregates, but does **not** override governance.

---

## 5. Error Handling Semantics
- If an agent fails, the orchestrator proceeds only as permitted by orchestration guards.
- On failure, the agent MUST still emit the AgentResult envelope with:
  - `status = failed`
  - `confidence = 0.0`
  - `key_findings = {}` and `metrics = []`
  - `suggested_penalties = []` and `veto_flags = []`
  - `notes` describing the failure scope if available
- **FAILED** indicates a technical/runtime error in agent execution.
- **VETOED** is a governance enforcement outcome handled elsewhere; agents do not emit VETOED statuses.

---

## 6. Determinism Rules
- Identical inputs MUST yield identical AgentResult outputs.
- Ordering of lists or dictionaries MUST NOT alter meaning.
- All numeric outputs MUST be sourced via MetricValue.SourceRef or explicitly marked unknown/not_applicable.
- If a numeric value lacks provenance, it must be flagged as unsourced (no invented numbers).

---

## 7. Traceability (Per-Agent)
Each agent below references the authoritative HLD v1.0 sections and the DDs where outputs are consumed.

### 7.1 Fundamentals Agent
- **HLD v1.0:** §3 (agent roster), §5 (AgentResult; holding outputs)
- **Consumption:** DD-05 Penalty Engine Spec, DD-06 Governance Rules, DD-07 Canonicalization Spec, DD-08 Orchestration Guards

### 7.2 Technical Agent
- **HLD v1.0:** §3 (agent roster), §5 (AgentResult; holding outputs)
- **Consumption:** DD-05 Penalty Engine Spec, DD-06 Governance Rules, DD-07 Canonicalization Spec, DD-08 Orchestration Guards

### 7.3 Macro / Regime Inputs
- **HLD v1.0:** §4 (portfolio pre-flight), §5 (regime inputs)
- **Consumption:** DD-06 Governance Rules, DD-07 Canonicalization Spec, DD-08 Orchestration Guards

### 7.4 Devil’s Advocate
- **HLD v1.0:** §3 (agent roster), §5 (AgentResult; counter-case)
- **Consumption:** DD-05 Penalty Engine Spec, DD-06 Governance Rules, DD-07 Canonicalization Spec, DD-08 Orchestration Guards

### 7.5 Data Integrity Officer (DIO)
- **HLD v1.0:** §3 (veto authority), §5 (DIOOutput), §7 (hard-stop rules)
- **Consumption:** DD-06 Governance Rules, DD-07 Canonicalization Spec, DD-08 Orchestration Guards

### 7.6 Global Risk Regime Architect (GRRA)
- **HLD v1.0:** §3 (short-circuit authority), §5 (GRRAOutput)
- **Consumption:** DD-06 Governance Rules, DD-07 Canonicalization Spec, DD-08 Orchestration Guards

### 7.7 Liquidity & Exit Feasibility Officer (LEFO)
- **HLD v1.0:** §3 (override authority), §5 (LEFOOutput)
- **Consumption:** DD-05 Penalty Engine Spec, DD-06 Governance Rules, DD-07 Canonicalization Spec, DD-08 Orchestration Guards

### 7.8 Portfolio Structure & Concentration Controller (PSCC)
- **HLD v1.0:** §3 (cap authority), §5 (PSCCOutput)
- **Consumption:** DD-05 Penalty Engine Spec, DD-06 Governance Rules, DD-07 Canonicalization Spec, DD-08 Orchestration Guards

---

## 8. Acceptance Criteria
This document is complete and valid if:
1. The AgentResult envelope is specified with all mandatory fields and invariants.
2. Every agent has explicit input and output contracts aligned to HLD v1.0 and prior DDs.
3. Holding vs portfolio scope is explicit for each agent.
4. Governance-authoritative vs advisory roles are explicit, with Chair non-override clarified.
5. Error handling semantics distinguish FAILED from governance outcomes.
6. Determinism rules prohibit non-sourced numeric outputs and require stable ordering.
7. Traceability links each agent to relevant HLD sections and DD-05/DD-06/DD-07 consumption points.

---

STATUS: DD-03 COMPLETE — Agent interfaces locked for portfolio-first execution.
