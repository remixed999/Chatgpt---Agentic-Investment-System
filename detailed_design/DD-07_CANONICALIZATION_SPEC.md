# DD-07 — Canonicalization Specification (Deterministic & Reproducible)

## 1. Purpose
Canonicalization ensures that **identical logical inputs produce identical decision outputs**, regardless of:
- input ordering
- execution timing
- run identifiers
- narrative text differences

This specification defines:
- deterministic ordering rules
- equivalence vs decision-significant fields
- canonical serialization format
- hashing rules
- replay invariants

---

## 2. Canonicalization Scope

Canonicalization applies to:
- `PortfolioSnapshot`
- `PortfolioConfig`
- `RunConfig`
- all HoldingPackets
- PortfolioCommitteePacket
- all scorecards, penalties, caps, and outcomes

Canonicalization does NOT apply to:
- runtime execution metadata
- timestamps used only for logging
- free-form narrative text

---

## 3. Deterministic Ordering Rules (MANDATORY)

All collections MUST be sorted deterministically before hashing.

### 3.1 List Ordering

| Structure | Ordering Rule |
|---------|---------------|
| Holdings | `holding_id` (lexicographic, case-sensitive) |
| Agent outputs | `agent_name` (lexicographic) |
| Penalty items | `category` → `reason` → `source_agent` |
| Concentration breaches | `breach_type` → `identifier` |
| Veto logs | `timestamp` → `agent_name` |

### 3.2 Dictionary Ordering
- All dictionaries MUST be serialized with keys sorted lexicographically.
- No insertion-order semantics allowed.

---

## 4. Equivalence vs Decision-Significant Fields

### 4.1 Fields EXCLUDED from Canonical Hash
These fields must NOT affect the canonical hash:

- `run_id`
- all execution timestamps:
  - `start_time`
  - `end_time`
  - `generated_at`
  - `retrieval_timestamp`
- execution duration fields
- agent execution timing metadata
- narrative-only fields:
  - `notes`
  - `limitations`
  - `disclaimers`
  - `recovery_suggestions`

### 4.2 Fields INCLUDED in Canonical Hash
These fields MUST affect the canonical hash:

- PortfolioSnapshot:
  - holdings (sorted)
  - weights
  - cash_pct
- PortfolioConfig:
  - base_currency
  - concentration limits
  - risk tolerance
- RunConfig:
  - run_mode
  - burn_rate_classification
  - staleness thresholds
  - penalty caps
- Metric values:
  - `value`
  - `unit`
  - `as_of_date`
- Scores:
  - dimension raw scores
  - weights
  - contributions
  - final_score
- Penalties:
  - category
  - reason
  - amount
- Outcomes:
  - portfolio_run_outcome
  - per_holding_outcomes
- Overrides and caps:
  - LEFO caps
  - PSCC caps
- Regime outputs:
  - regime_label
  - regime_confidence
  - do_not_trade_flag

---

## 5. Canonical Serialization Format

### 5.1 JSON Canonical Form
- UTF-8 encoding
- no whitespace
- sorted keys
- stable numeric formatting

Example:
```json
{"holdings":[{"holding_id":"ABC","final_score":72}],"portfolio_run_outcome":"COMPLETED"}
```

### 5.2 Numeric Formatting
- Integers serialize without decimal points.
- Floats must be serialized with:
  - a dot (`.`) as the decimal separator
  - no trailing zeros
  - no exponent notation
- NaN and Infinity are not allowed in canonical data. They must be mapped to `null` before serialization and excluded from hashing unless explicitly part of a decision.

### 5.3 Boolean and Null Values
- Booleans must be serialized as `true` or `false`.
- Null values must be serialized as `null` and only included when the field is decision-significant.

### 5.4 String Normalization
- Strings must be UTF-8 encoded.
- Preserve case and punctuation (no lowercasing).
- Trim leading/trailing whitespace only for fields defined as identifiers (e.g., `holding_id`, `agent_name`).

---

## 6. Hashing Rules

### 6.1 Algorithms
- Use SHA-256 over the canonical JSON string.
- Output format: lowercase hex string.

### 6.2 Hash Granularity
The following hashes MUST be computed and stored:

| Hash | Canonical Input |
|------|------------------|
| `snapshot_hash` | Canonical `PortfolioSnapshot` |
| `config_hash` | Canonical `PortfolioConfig` |
| `run_config_hash` | Canonical `RunConfig` |
| `holding_packet_hash` | Each canonical HoldingPacket |
| `committee_packet_hash` | Canonical PortfolioCommitteePacket |
| `decision_hash` | Canonical final outcome packet |

### 6.3 Composite Run Hash
A `run_hash` MUST be computed as the SHA-256 of:
```json
{
  "snapshot_hash":"...",
  "config_hash":"...",
  "run_config_hash":"...",
  "committee_packet_hash":"...",
  "decision_hash":"..."
}
```
The composite hash binds the run to all decision-significant inputs and outputs.

---

## 7. Replay Invariants

To pass replay validation, the following must hold:
- identical canonical inputs produce identical hashes
- `decision_hash` matches for identical logical runs
- `run_hash` is stable across execution environments
- ordering of any list or map does not affect results

---

## 8. Validation & Enforcement

### 8.1 Validation Checks
Implement checks that fail fast if:
- canonicalization rules are violated
- non-deterministic ordering is detected
- excluded fields appear in the canonical payload

### 8.2 Error Handling
- Any canonicalization failure must produce a `CANONICALIZATION_ERROR` with the offending path.
- Failures are blocking; the run must stop.

---

## 9. Versioning

- This specification is versioned as DD-07 v1.0.
- Any change to canonical rules must increment the version and rebaseline hashes.

---

## 10. Summary
Canonicalization is mandatory for reproducibility, auditability, and governance. All decision-critical data must obey deterministic ordering and stable serialization to guarantee consistent hashes across time and environments.
