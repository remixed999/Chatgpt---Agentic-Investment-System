# SCHEMA_SPECIFICATIONS.md

## 1. Document Conventions

### Purpose
This document defines the authoritative, field-level schema specifications for the system’s core data structures during Detailed Design (DD). It is the single source of truth for requiredness, nullability, constraints, and cross-field invariants for the schemas listed in this document.

### How to read schema tables
Each schema includes a field table with these columns:
- **Field**: Exact field name.
- **Type**: Declared type from the Type System section.
- **Required**: **Yes** if the field must be present in the object; **No** if it may be omitted.
- **Nullable**: **Yes** if the field may explicitly be set to null; **No** if null is not permitted.
- **Default**: The default value if any (explicitly stated). If none, use “—”.
- **Constraints**: Allowed values, ranges, formats, or conditional requirements.
- **Notes**: Clarifying guidance, including traceability and scope.

### Required vs Optional vs Nullable semantics
- **Required**: Field must appear in the object.
- **Optional**: Field may be omitted entirely.
- **Nullable**: Field may be present with a null value. Nullability does **not** imply optionality.

### Null semantics
- **Null** indicates **Unknown** only (not captured, not supplied, or not determinable).
- **Not Applicable** must be represented explicitly and never via null.
- **Unknown vs Not Applicable** must be unambiguous in every schema (see Type System: Availability).

### Traceability rules
- Every schema must trace to **HLD v1.0 §5 (Data Models & Contracts)** and list applicable requirement IDs.
- If the HLD text or requirement IDs are unavailable in the repository, this must be flagged as a **DESIGN DECISION** and traced as “TBD” pending HLD inclusion.

### Schema versioning rules
- Schema versions are tracked at the document level. This document represents **DD-01**.
- Any schema change requires a new DD revision and explicit approval.

---

## 2. Type System

### Primitive types
- **String**: UTF-8 text.
- **Boolean**: True/False.
- **Integer**: Whole numbers.
- **Decimal**: Fixed-point numeric with precision defined by constraints.
- **Date**: Calendar date (no time).
- **DateTime**: Timestamp with timezone offset.

### Constrained types
- **NonEmptyString**: String with length ≥ 1.
- **IdentifierString**: NonEmptyString with no leading/trailing whitespace.
- **CanonicalKey**: IdentifierString used for deduplication and canonicalization references.

### Enum definitions
- **Availability**:
  - **KNOWN**: Value is known and present.
  - **UNKNOWN**: Value is not known (represented as null in value-bearing fields).
  - **NOT_APPLICABLE**: Field does not apply to the entity; must be explicit, never null.

> **DESIGN DECISION:** The Availability enum is introduced to enforce the “Unknown vs Not Applicable” rule in the absence of explicit HLD guidance in the repository. Traceability is marked TBD until HLD v1.0 §5 is available locally.

### Collection types
- **Array<T>**: Ordered list of items of type T.
- **Object**: Structured fields per schema table.

### Schema composition rules
- **Embedded** schemas are reusable objects nested inside other schemas.
- **Portfolio-level** schemas describe the portfolio as a whole.
- **Holding-level** schemas describe a specific holding within a portfolio.
- **No implicit defaults**: if a field is required, it must be explicitly provided.

---

## 3. Core Primitive Schemas

### 3.1 InstrumentIdentity

**Traces to:** HLD v1.0 §5 (Data Models & Contracts), requirement IDs TBD.

**Level:** Embedded (used at Holding level, potentially Portfolio level where applicable).

**Description:**
Defines the canonical identity fields for an instrument. Provides a consistent identity across sources without implying pricing, valuation, or FX logic.

**Field Table**

| Field | Type | Required | Nullable | Default | Constraints | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| identifier_type | NonEmptyString | Yes | No | — | Must be one of the identifier types listed in HLD v1.0 §5. | Traceability pending HLD inclusion. |
| identifier_value | IdentifierString | Yes | No | — | Must conform to the format required by identifier_type. | No leading/trailing whitespace. |
| instrument_name | String | No | Yes | — | If present, must be descriptive and non-empty. | Null indicates unknown. |
| display_symbol | String | No | Yes | — | If present, must be the human-readable display symbol. | Optional for non-ticker instruments. |
| canonical_key | CanonicalKey | No | Yes | — | If present, must be stable across sources. | Canonicalization acknowledgement only; no logic specified here. |

**Cross-field invariants**
- identifier_type and identifier_value must be provided together.
- If canonical_key is present, it must map to the same instrument as identifier_type + identifier_value.

**DESIGN DECISIONS**
- Identifier type enumeration is marked TBD until HLD v1.0 §5 is present in the repository.

---

### 3.2 SourceRef

**Traces to:** HLD v1.0 §5 (Data Models & Contracts), requirement IDs TBD.

**Level:** Embedded.

**Description:**
Represents the provenance of any sourced data point. Enforces the “no unsourced numbers” requirement.

**Field Table**

| Field | Type | Required | Nullable | Default | Constraints | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| source_name | NonEmptyString | Yes | No | — | Must match an allowed source name from HLD v1.0 §5. | Traceability pending HLD inclusion. |
| source_id | IdentifierString | No | Yes | — | If present, must be stable for the source. | Null indicates unknown. |
| retrieval_timestamp | DateTime | Yes | No | — | Must include timezone offset. | Required for auditability. |
| source_notes | String | No | Yes | — | Free-text notes, if provided. | Null indicates unknown. |

**Cross-field invariants**
- source_name must be present for any SourceRef.
- retrieval_timestamp must be present to ensure auditability.

**DESIGN DECISIONS**
- Allowed source_name values are TBD pending HLD v1.0 §5 availability in the repository.

---

### 3.3 MetricValue

**Traces to:** HLD v1.0 §5 (Data Models & Contracts), requirement IDs TBD.

**Level:** Embedded (used at Portfolio or Holding level depending on metric context).

**Description:**
Represents a single numeric metric with explicit provenance and applicability semantics. Enforces portfolio-first design by allowing metrics at portfolio or holding scope without implying execution logic.

**Field Table**

| Field | Type | Required | Nullable | Default | Constraints | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| metric_name | NonEmptyString | Yes | No | — | Must map to a metric defined in HLD v1.0 §5. | Traceability pending HLD inclusion. |
| value | Decimal | No | Yes | — | If present, must be numeric and comply with metric-specific precision. | Null indicates unknown only. |
| availability | Availability | Yes | No | — | Must be KNOWN, UNKNOWN, or NOT_APPLICABLE. | Enforces Unknown vs Not Applicable distinction. |
| unit | String | No | Yes | — | Required if value is present and metric has units. | No default base currency. |
| as_of_date | Date | No | Yes | — | If present, must be the date the metric is valid for. | Null indicates unknown. |
| source_ref | SourceRef | No | Yes | — | Required when value is present. | Enforces “no unsourced numbers.” |

**Cross-field invariants**
- If availability = KNOWN, value must be present and non-null.
- If availability = UNKNOWN, value must be null.
- If availability = NOT_APPLICABLE, value must be null and metric_name must still be present.
- If value is present, source_ref must be present.
- If unit is required by the metric, it must be explicitly provided; no default base currency is assumed.

**DESIGN DECISIONS**
- Metric names and unit requirements are TBD pending HLD v1.0 §5 availability in the repository.

---

## 4. Schema-Level Governance Rules

### VETOED vs FAILED distinction
- **VETOED**: A deterministic governance rule explicitly blocks an output due to a hard constraint violation.
- **FAILED**: A process or validation cannot complete due to missing or invalid data that prevents evaluation.

### Examples
- **VETOED**: A holding violates a hard exclusion rule; output is blocked.
- **FAILED**: A required metric is missing and cannot be sourced; evaluation halts without a determinative veto.

### Precedence rules
- **VETOED** takes precedence over **FAILED** if both could apply; a known rule violation is stronger than incompleteness.
- **FAILED** applies only when no deterministic veto can be established due to missing information.

---

STATUS: DD-01 COMPLETE — Awaiting approval to proceed to DD-02 (DATA_CONTRACTS.md)
