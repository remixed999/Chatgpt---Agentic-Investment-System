# SCHEMA_SPECIFICATIONS.md

## SECTION 1 — Document Conventions

### Purpose
This document defines the design-time schema specifications for the system’s data models, derived strictly from HLD v1.0 §5 (Data Models & Contracts), with a portfolio-first orientation and no implementation logic.

### How to Read Schema Tables
Each schema is described using a field table with the columns:

- **Field** — canonical field name.
- **Type** — design-time type or constrained type.
- **Required** — whether the field must appear in the schema.
- **Nullable** — whether the field may explicitly carry null when present.
- **Default** — only if explicitly specified in HLD.
- **Constraints** — any format or semantic limitations specified by HLD.
- **Notes** — clarifications, including traceability.

### Required vs Optional vs Nullable Semantics
- **Required**: Field must be present in every instance.
- **Optional**: Field may be omitted entirely.
- **Nullable**: Field may be present with an explicit null value.

**DESIGN DECISION:** Nullable is used only where HLD explicitly permits null semantics (MetricValue.value). No other fields are nullable unless implied by HLD.

### Null vs Unknown vs Not Applicable (Explicit Semantics)
Derived from MetricValue semantic rules in HLD:

- **Null**: `value = None` explicitly indicates absence of a value. Allowed only for MetricValue.value.
- **Unknown/Missing**: `value = None` and `missing_reason` provided indicates unknown data and may incur penalty if critical.
- **Not Applicable**: `not_applicable = true` indicates the metric is irrelevant for this instrument/sector; no penalty applies.
- **Schema Violation**: `value = None` and `not_applicable = false` and `missing_reason = None`.

### Traceability Rules to HLD v1.0 §5
- Every schema explicitly cites relevant HLD §5 subsections.
- No fields, defaults, or constraints may be introduced beyond those listed in HLD §5.

### Schema Versioning Rules (Document-Level Only)
- Versioning applies only to this document (e.g., DD-01).
- No runtime schema versioning is implied.

**DESIGN DECISION:** Document-level versioning supports DD phase change control while preserving HLD as authoritative.

---

## SECTION 2 — Type System

### Primitive Types
- `string`
- `float`
- `bool`
- `datetime` (tz-aware UTC where specified)

### Constrained Types
- **CurrencyCode**: ISO currency code.
- **CountryCode**: ISO country code.
- **DateTimeUTC**: tz-aware UTC timestamp.

### Enum Definitions
None. HLD provides examples only and does not define closed enumerations for these schemas.

### Collection Types
- `list<T>`
- `dict<K,V>`

### Schema Composition Rules
- **Holding-level**: Applies per holding.
- **Embedded**: Used within other schemas.

Composition:
- InstrumentIdentity → Holding-level
- SourceRef → Embedded
- MetricValue → Embedded

---

## SECTION 3 — Core Primitive Schemas

### 3.1 InstrumentIdentity

**Description**
Canonical identity for a holding-level instrument. Required by HLD to include ticker, exchange, and currency.

**Scope**
Holding-level

**Field Table**

| Field | Type | Required | Nullable | Default | Constraints | Notes |
|-----|-----|-----|-----|-----|-----|-----|
| ticker | string | Yes | No | — | — | Required by HLD. |
| exchange | string | Yes | No | — | Free-form in v0.1 | Required by HLD. |
| country | CountryCode | No | No | — | ISO country code | Optional per HLD. |
| currency | CurrencyCode | Yes | No | — | ISO currency code | Required by HLD. |
| isin | string | No | No | — | — | Optional per HLD. |
| instrument_type | string | No | No | — | Examples only | Not an enum per HLD. |
| share_class | string | No | No | — | Examples only | Optional per HLD. |

**Cross-Field Invariants**
- `ticker`, `exchange`, and `currency` are independently required; absence of any violates identity completeness.

**Traceability**
HLD v1.0 §5.1 (R9)

---

### 3.2 SourceRef

**Description**
Provenance metadata for sourced data.

**Scope**
Embedded

**Field Table**

| Field | Type | Required | Nullable | Default | Constraints | Notes |
|-----|-----|-----|-----|-----|-----|-----|
| origin | string | No | No | — | Examples only | Not an enum. |
| as_of_date | DateTimeUTC | Yes | No | — | tz-aware UTC | Required by HLD. |
| retrieval_timestamp | DateTimeUTC | Yes | No | — | tz-aware UTC | Required by HLD. |
| original_timezone | string | No | No | — | — | Optional. |
| provider_name | string | No | No | — | — | Optional. |
| provider_version | string | No | No | — | — | Optional. |
| notes | string | No | No | — | — | Optional. |

**Cross-Field Invariants**
- `as_of_date` and `retrieval_timestamp` must always be present.

**Traceability**
HLD v1.0 §5.1 (R2)

---

### 3.3 MetricValue

**Description**
Metric wrapper governing value presence, provenance, and applicability semantics.

**Scope**
Embedded

**Field Table**

| Field | Type | Required | Nullable | Default | Constraints | Notes |
|-----|-----|-----|-----|-----|-----|-----|
| value | float \| string \| bool | No | Yes | — | Allowed primitives only | Null indicates unknown only. |
| unit | string | No | No | — | Examples only | Optional per HLD. |
| missing_reason | string | No | No | — | Required if value is null and not_applicable = false | Clarifies unknown/missing. |
| not_applicable | bool | No | No | False | — | Default false per HLD. |
| source_ref | SourceRef | Conditional | No | — | Required if value present | Enforces provenance. |

**Cross-Field Invariants**
- If `value` is present → `source_ref` must be present.
- If `not_applicable = true` → no penalty applies.
- If `value = null` and `missing_reason` is set → unknown/missing.
- If `value = null` and `not_applicable = false` and `missing_reason = null` → schema violation (FAILED).

**Traceability**
HLD v1.0 §5.1 (R2, R3)

---

STATUS: DD-01 COMPLETE — Sections 1–4 finalized.

---

## SECTION 4 — Agent & Registry Schemas (Authoritative)

### 4.1 AgentResult

**Description**
Standardized agent output envelope for all agent emissions.

**Scope**
Holding-level and portfolio-level

**Field Table**

| Field | Type | Required | Nullable | Default | Constraints | Notes |
|-----|-----|-----|-----|-----|-----|-----|
| agent_name | string | Yes | No | — | — | Canonical agent identifier. |
| status | string | Yes | No | — | "completed" \| "failed" \| "skipped" | Matches HLD R5. |
| confidence | float | Yes | No | — | 0.0–1.0 | Required for all agents. |
| key_findings | dict<string, any> | Yes | No | — | Agent-specific structure | Structured findings per agent. |
| metrics | list<MetricValue> | Yes | No | — | MetricValue items only | All metrics must carry SourceRef when value present. |
| suggested_penalties | list<PenaltyItem> | Yes | No | — | PenaltyItem only | Advisory only; enforcement elsewhere. |
| veto_flags | list<string> | Yes | No | — | — | Advisory-only flags. |
| counter_case | string | No | No | — | — | Devil’s Advocate narrative only. |
| notes | string | No | No | — | — | Optional agent notes. |

**Cross-Field Invariants**
- `confidence` must be within 0.0–1.0 inclusive.
- `metrics` entries must conform to MetricValue rules (SourceRef required when value present).
- `suggested_penalties` entries must conform to PenaltyItem.

**Traceability**
HLD v1.0 §5 (AgentResult R5)

---

### 4.2 PenaltyItem

**Description**
Advisory penalty item emitted by agents; normalized by Penalty Engine.

**Scope**
Embedded

**Field Table**

| Field | Type | Required | Nullable | Default | Constraints | Notes |
|-----|-----|-----|-----|-----|-----|-----|
| category | string | Yes | No | — | "A" \| "B" \| "C" \| "D" \| "E" \| "F" | Penalty category. |
| reason | string | Yes | No | — | Stable reason key | Deterministic reasons only. |
| amount | float | Yes | No | — | Negative values only | Advisory amount. |
| source_agent | string | Yes | No | — | — | Agent name emitting the item. |

**Traceability**
HLD v1.0 §5 (PenaltyItem)

---

### 4.3 ConfigSnapshot

**Description**
Frozen configuration snapshot referenced by DIO and Penalty Engine.

**Scope**
Portfolio-level

**Field Table**

| Field | Type | Required | Nullable | Default | Constraints | Notes |
|-----|-----|-----|-----|-----|-----|-----|
| hard_stop_field_registry | HardStopFieldRegistry | Yes | No | — | — | Hard-stop registry (see 4.4). |
| penalty_critical_field_registry | PenaltyCriticalFieldRegistry | Yes | No | — | — | Penalty-critical registry (see 4.5). |
| scoring_rubric_version | string | Yes | No | — | — | Version tag for scorecard/penalty rubric. |
| agent_prompt_versions | dict<string, string> | Yes | No | — | — | Map of agent_name → version. |

**Traceability**
HLD v1.0 §5 (ConfigSnapshot R14)

---

### 4.4 HardStopFieldRegistry

**Description**
Registry of fields that trigger immediate veto when missing.

**Scope**
Portfolio-level config object

**Field Table**

| Field | Type | Required | Nullable | Default | Constraints | Notes |
|-----|-----|-----|-----|-----|-----|-----|
| identity_fields_all_companies | list<string> | Yes | No | — | Must include ticker/exchange/currency | Always required for every holding. |
| burn_rate_fields_conditional | list<string> | Yes | No | — | cash/runway/burn_rate | Required only when burn-rate classification=true. |
| portfolio_level_fields | list<string> | Yes | No | — | Must include base_currency | Required at portfolio level. |

**Traceability**
HLD v1.0 §5 (HardStopFieldRegistry R14)

---

### 4.5 PenaltyCriticalFieldRegistry

**Description**
Registry of fields that trigger penalties (not vetoes) when missing.

**Scope**
Portfolio-level config object

**Field Table**

| Field | Type | Required | Nullable | Default | Constraints | Notes |
|-----|-----|-----|-----|-----|-----|-----|
| fundamentals | list<string> | Yes | No | — | — | Core fundamentals fields. |
| fundamentals_conditional_burn_rate | list<string> | Yes | No | — | cash/runway/burn_rate | Penalty-critical when burn-rate=false. |
| technicals | list<string> | Yes | No | — | — | Core technical fields. |
| liquidity | list<string> | Yes | No | — | — | Core liquidity fields. |
| macro_regime | list<string> | Yes | No | — | — | Macro/regime inputs. |

**Cross-Field Invariants**
- Identity fields (ticker, exchange, currency) MUST NOT appear here; they belong only to HardStopFieldRegistry.

**Traceability**
HLD v1.0 §5 (PenaltyCriticalFieldRegistry R14)
