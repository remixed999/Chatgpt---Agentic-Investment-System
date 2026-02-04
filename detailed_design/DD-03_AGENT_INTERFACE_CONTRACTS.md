# DD-03 — Agent Interface Contracts (Portfolio-First)

## 1. Purpose
This document defines the **formal input/output contracts** for every agent in the system. Agents emit **structured signals only**; they do **not** make governance decisions.

Invariants:
- Agents **never** issue final scores, penalties, or recommendation categories.
- Agents **never** override governance or precedence rules.
- All outputs are portfolio-first and auditable.

---

## 2. Agent Interface Standard (MANDATORY)
All agents MUST emit the common **AgentResult** envelope. This wrapper is mandatory regardless of scope or outcome.

### 2.1 AgentResult Envelope (Required Fields)
- **agent_name**
- **agent_version**
- **scope**: `holding` | `portfolio`
- **status**: `completed` | `failed` | `skipped`
- **confidence**: 0.0–1.0
- **outputs**: agent-specific payload only
- **veto_flags**: advisory-only flags (if applicable)
- **limitations**: explicit known limitations or gaps
- **source_refs**: required when any numeric value appears in outputs

### 2.2 Envelope Invariants
- Agents **never emit final scores**.
- Agents **never apply penalties**.
- Agents **never override governance** (veto/short-circuit/caps are enforced elsewhere).
- Any numeric value in `outputs` requires traceable provenance via `source_refs`.

---

## 3. Per-Agent Interface Definitions
Each agent below MUST conform to the AgentResult envelope and provide the explicit inputs/outputs listed. All outputs are **advisory** unless governance rules explicitly state otherwise.

### 3.A Fundamentals Agent (Holding-Scoped)
**Inputs**
- HoldingSnapshot
- Seeded financial data (sourced MetricValue inputs)

**Outputs (within AgentResult.outputs)**
- `fundamental_metrics` (structured, sourced)
- `confidence`


### 3.B Technical Agent (Holding-Scoped)
**Inputs**
- Price/volume time series

**Outputs (within AgentResult.outputs)**
- `technical_signals` (structured, sourced)
- `confidence`


### 3.C Macro / Regime Inputs (Portfolio-Scoped)
**Inputs**
- Portfolio-level macro/regime indicators (sourced)

**Outputs (within AgentResult.outputs)**
- `regime_indicators` (no policy decisions)
- `confidence`


### 3.D Devil’s Advocate (Holding-Scoped)
**Inputs**
- HoldingSnapshot
- All prior analytical outputs (read-only)

**Outputs (within AgentResult.outputs)**
- `risk_flags`
- `unresolved_fatal_risk` (boolean)
- `narrative_limitations`
- `confidence`


### 3.E Data Integrity Officer (DIO) (Holding-Scoped + Portfolio-Scoped)
**Inputs**
- HoldingSnapshot and PortfolioSnapshot
- All MetricValue-bearing inputs and SourceRefs
- Registry snapshots (hard-stop vs penalty-critical)

**Outputs (within AgentResult.outputs)**
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

**Outputs (within AgentResult.outputs)**
- `regime_label`
- `regime_confidence`
- `do_not_trade_flag`


### 3.G Liquidity & Exit Feasibility Officer (LEFO) (Holding-Scoped)
**Inputs**
- HoldingSnapshot
- Liquidity and spread inputs (sourced)

**Outputs (within AgentResult.outputs)**
- `liquidity_grade`
- `hard_override_flags`


### 3.H Portfolio Structure & Concentration Controller (PSCC) (Portfolio-Scoped)
**Inputs**
- PortfolioSnapshot
- Holding-level outputs (read-only)
- PortfolioConfig

**Outputs (within AgentResult.outputs)**
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
- Macro / Regime Inputs (portfolio context)

### 4.3 Governance Authority vs Advisory
- **Governance-authoritative**: DIO (veto authority), GRRA (short-circuit authority), LEFO/PSCC (override/cap authority). Outputs are still advisory signals; enforcement is external.
- **Advisory-only**: Fundamentals, Technical, Devil’s Advocate, Macro/Regime Inputs.
- **Chair** consumes all outputs and aggregates but does **not** override governance.

---

## 5. Error Handling Semantics
- If an agent fails, the orchestrator **continues** where permitted by orchestration guards.
- On failure, the agent MUST still emit the AgentResult envelope with:
  - `status = failed`
  - `confidence = 0.0`
  - `outputs` present but empty or explicitly marked as unavailable
  - `limitations` describing the failure scope
- **FAILED** indicates a technical/runtime error in agent execution.
- **VETOED** is governance enforcement handled elsewhere; agents do not emit VETOED outcomes.

---

## 6. Determinism Rules
- Identical inputs MUST yield identical AgentResult outputs.
- Ordering of lists or dictionaries MUST NOT alter meaning.
- All numeric outputs MUST be sourced via `source_refs` or explicitly marked unknown/not_applicable.
- If a numeric value lacks provenance, DIO must flag it as unsourced (no invented numbers).

---

## 7. Traceability (Per-Agent)
Each agent below references the authoritative HLD v1.0 sections and the DDs where the outputs are consumed.

### 7.1 Fundamentals Agent
- **HLD v1.0**: §3 (agent roster), §5 (AgentResult; holding outputs)
- **Consumption**: DD-05 Penalty Engine (metric penalties), DD-06 Governance Rules (advisory-only), DD-07 Canonicalization (ordering), DD-08 Orchestration Guards (output conformance)

### 7.2 Technical Agent
- **HLD v1.0**: §3 (agent roster), §5 (AgentResult; holding outputs)
- **Consumption**: DD-05 Penalty Engine, DD-06 Governance Rules, DD-07 Canonicalization, DD-08 Orchestration Guards

### 7.3 Macro / Regime Inputs
- **HLD v1.0**: §4 (portfolio pre-flight), §5 (macro/regime inputs)
- **Consumption**: DD-06 Governance Rules (policy short-circuit context), DD-07 Canonicalization, DD-08 Orchestration Guards

### 7.4 Devil’s Advocate
- **HLD v1.0**: §3 (agent roster), §5 (AgentResult; counter-case)
- **Consumption**: DD-05 Penalty Engine (risk flag penalties), DD-06 Governance Rules (risk officer veto conditions), DD-07 Canonicalization, DD-08 Orchestration Guards

### 7.5 Data Integrity Officer (DIO)
- **HLD v1.0**: §3 (veto authority), §5 (DIOOutput), §7 (hard-stop rules)
- **Consumption**: DD-06 Governance Rules (veto precedence), DD-07 Canonicalization (ordering), DD-08 Orchestration Guards (provenance/staleness gates)

### 7.6 Global Risk Regime Architect (GRRA)
- **HLD v1.0**: §3 (short-circuit authority), §5 (GRRAOutput)
- **Consumption**: DD-06 Governance Rules (short-circuit), DD-07 Canonicalization, DD-08 Orchestration Guards

### 7.7 Liquidity & Exit Feasibility Officer (LEFO)
- **HLD v1.0**: §3 (override authority), §5 (LEFOOutput)
- **Consumption**: DD-06 Governance Rules (override precedence), DD-05 Penalty Engine (liquidity penalties where applicable), DD-07 Canonicalization, DD-08 Orchestration Guards

### 7.8 Portfolio Structure & Concentration Controller (PSCC)
- **HLD v1.0**: §3 (cap authority), §5 (PSCCOutput)
- **Consumption**: DD-06 Governance Rules (cap precedence), DD-05 Penalty Engine (concentration penalties where applicable), DD-07 Canonicalization, DD-08 Orchestration Guards

---

## 8. Acceptance Criteria
DD-03 is complete and valid only if:
1. Every agent uses the AgentResult envelope with all required fields.
2. Agent outputs are explicitly defined for each agent listed in §3.
3. Scope rules clearly separate holding vs portfolio responsibilities.
4. Governance authority is declared as advisory-only at the agent level.
5. Error handling distinguishes FAILED from governance outcomes.
6. Determinism and provenance rules are explicit and enforce “no invented numbers.”
7. Traceability references HLD v1.0 and DD-05/DD-06/DD-07/DD-08 for output consumption.

