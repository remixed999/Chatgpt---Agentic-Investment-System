# DD-09 — Test Fixture Specifications

## 1. Purpose & Scope
1.1 This document defines deterministic, portfolio-first test fixtures used for unit and integration tests across the orchestration, governance, penalty, and canonicalization subsystems.
1.2 Fixtures are **deterministic inputs and expected outputs** that enable repeatable testing with no runtime ambiguity.
1.3 Hard-stops (vetoes) always take precedence over penalties. Penalties never override vetoes.
1.4 Scope includes:
- Portfolio snapshots, run configs, and configuration snapshots
- Seeded data used by scoring and penalties
- Expected output packets for holdings and portfolio runs

## 2. Fixture Format Standards
2.1 **File Naming Convention** (fixture files only; folder may be created later):
- `fixtures/portfolio/<fixture_name>.json`
- `fixtures/config/<fixture_name>.json`
- `fixtures/seeded/<fixture_name>.json`
- `fixtures/expected/<fixture_name>.json`
- `fixtures/matrix/<fixture_name>.json`

2.2 **Required Metadata** (present at top-level of each fixture file):
- `fixture_id` (string, stable identifier)
- `version` (string, semantic or date-based)
- `description` (string)
- `created_at_utc` (string, fixed ISO8601 UTC)

2.3 **Deterministic Timestamp Policy**
- All timestamps in fixtures MUST be fixed ISO8601 UTC strings (e.g., `2025-01-01T00:00:00Z`).
- No `now()` or relative time expressions in fixture data.
- Retrieval timestamps are deterministic, even if they represent historical retrieval times.

2.4 **SourceRef Requirements** (for any sourced numeric value or dataset):
- `origin` (string, source system or provider)
- `as_of_date` (string, ISO8601 date or datetime, UTC)
- `retrieval_timestamp` (string, ISO8601 UTC)

2.5 **Portfolio-First Invariant**
- Any fixture that includes holdings must include a portfolio-level container (`PortfolioSnapshot`) and produce a portfolio-level expected outcome.

## 3. Fixture Types
3.1 **PortfolioSnapshot Fixtures**
- `PortfolioSnapshot_N1` (single holding)
- `PortfolioSnapshot_N3` (three holdings)
- `PortfolioSnapshot_N10` (ten holdings)
- Each snapshot includes: `portfolio_id`, `base_currency`, `as_of_date`, `holdings[]`, `cash_pct` (if applicable), and holdings `holding_id`, `ticker`/`identifier`, `weight`.

3.2 **RunConfig Fixtures**
- `RunConfig_FAST`
- `RunConfig_DEEP`
- Each config includes: `run_mode`, penalty caps, staleness thresholds, burn-rate classification rules, and orchestration guard thresholds.

3.3 **ConfigSnapshot Fixtures**
- Registry configuration snapshots (agent registry, rules registry, scoring rubric)
- Must include `rubric_version` and any referenced registry identifiers

3.4 **Seeded Data Fixtures**
- Financials (e.g., cash, runway, burn-rate flags)
- Price/volume series
- Macro data
- FX rates
- All seeded records must include `SourceRef` metadata.

3.5 **Expected Output Fixtures**
- `per_holding_outcomes` (including status, penalties, veto reasons)
- `portfolio_run_outcome` (status, veto reason if any)
- Penalty breakdown (by category)
- Canonical hashes:
  - `snapshot_hash`
  - `config_hash`
  - `run_config_hash`
  - `decision_hash`
  - `run_hash`

## 4. Test Matrix (Deterministic Given/When/Then)

### TF-01 — Happy Path (DEEP, N=3, All Complete)
- **Given** `PortfolioSnapshot_N3`, `RunConfig_DEEP`, all seeded data present and sourced.
- **When** orchestration executes the full run.
- **Then** `portfolio_run_outcome=COMPLETED`, all holdings `COMPLETED`, and canonical hash generated.
- **Minimal Required Inputs**: `portfolio_id`, `base_currency`, `holdings[]`, `run_mode=DEEP`, required seeded financials + price/volume + macro + FX with `SourceRef`.
- **Traceability**: DD-01 Schema Specifications; DD-02 Data Contracts; DD-04 Orchestration Flow; DD-05 Penalty Engine Specification; DD-07 Canonicalization Specification; DD-08 Orchestration Guards.

### TF-02 — Missing Base Currency
- **Given** a `PortfolioSnapshot` missing `base_currency`.
- **When** validation runs.
- **Then** portfolio is `VETOED` with DIO integrity veto; minimal outputs only (no penalties, no scores).
- **Minimal Required Inputs**: `portfolio_id`, `holdings[]`, missing `base_currency`.
- **Traceability**: DD-01 Schema Specifications; DD-02 Data Contracts; DD-08 Orchestration Guards.

### TF-03 — GRRA Do-Not-Trade
- **Given** GRRA output with `do_not_trade=true` for the portfolio.
- **When** orchestration evaluates governance.
- **Then** portfolio `SHORT_CIRCUITED`, all holdings `SHORT_CIRCUITED`.
- **Minimal Required Inputs**: `PortfolioSnapshot`, GRRA output with `do_not_trade=true`.
- **Traceability**: DD-04 Orchestration Flow; DD-06 Governance Rules; DD-08 Orchestration Guards.

### TF-04 — Holding Identity Schema Violation
- **Given** a portfolio with one holding missing required identity fields.
- **When** holding validation runs.
- **Then** the invalid holding `FAILED`, remaining holdings processed; portfolio `COMPLETED` if failure rate is under threshold.
- **Minimal Required Inputs**: `PortfolioSnapshot` with >=2 holdings; one holding missing identity fields; failure threshold from `RunConfig`.
- **Traceability**: DD-01 Schema Specifications; DD-04 Orchestration Flow; DD-08 Orchestration Guards.

### TF-05 — Burn-Rate Company Missing Cash
- **Given** a burn-rate classified holding missing `cash`.
- **When** penalty evaluation runs.
- **Then** holding `VETOED`, penalties zeroed for that holding.
- **Minimal Required Inputs**: holding with burn-rate flag, missing `cash`, seeded financials with `SourceRef`.
- **Traceability**: DD-05 Penalty Engine Specification; DD-06 Governance Rules; DD-08 Orchestration Guards.

### TF-06 — Non-Burn-Rate Missing Cash/Runway
- **Given** non-burn-rate holding missing `cash` and/or `runway` and not marked `not_applicable`.
- **When** penalties are computed in DEEP.
- **Then** Category A penalty `-6` applied.
- **Minimal Required Inputs**: holding with burn-rate flag false, missing `cash`/`runway`, `run_mode=DEEP`.
- **Traceability**: DD-05 Penalty Engine Specification; DD-06 Governance Rules.

### TF-07 — Not Applicable Cash/Runway
- **Given** holding marked `not_applicable` for cash/runway, with missing values.
- **When** penalties are computed.
- **Then** no penalty is applied for missing cash/runway.
- **Minimal Required Inputs**: holding `not_applicable` flag, missing cash/runway fields.
- **Traceability**: DD-05 Penalty Engine Specification; DD-06 Governance Rules.

### TF-08 — Staleness Penalty Threshold Hit
- **Given** financials staleness at 100 days in DEEP.
- **When** staleness evaluation runs.
- **Then** Category B penalty `-5` applied.
- **Minimal Required Inputs**: `run_mode=DEEP`, financials with `as_of_date` 100 days before `created_at_utc`.
- **Traceability**: DD-05 Penalty Engine Specification; DD-06 Governance Rules.

### TF-09 — Staleness Hard-Stop Exceeded
- **Given** financials staleness at 200 days in DEEP.
- **When** staleness evaluation runs.
- **Then** DIO veto applied; no Category B penalty assessed.
- **Minimal Required Inputs**: `run_mode=DEEP`, financials with `as_of_date` 200 days before `created_at_utc`.
- **Traceability**: DD-05 Penalty Engine Specification; DD-06 Governance Rules; DD-08 Orchestration Guards.

### TF-10 — Corporate Action Split Within 90 Days
- **Given** a corporate action split within 90 days of `as_of_date`.
- **When** penalties are computed.
- **Then** Category F penalty `-6` applied and Category B not applied for staleness.
- **Minimal Required Inputs**: corporate action record with split within 90 days, holding identity.
- **Traceability**: DD-05 Penalty Engine Specification; DD-06 Governance Rules.

### TF-11 — Unsourced Numbers Detected
- **Given** seeded data includes numeric fields without `SourceRef`.
- **When** validation runs.
- **Then** DIO integrity veto is triggered; expected outcome is `VETOED`.
- **And** in debug-mode (if explicitly allowed by run config), validation records the violations but still produces diagnostic outputs without changing the veto outcome.
- **Minimal Required Inputs**: seeded data with missing `SourceRef`, `run_mode` and `debug_mode` flag in `RunConfig`.
- **Traceability**: DD-02 Data Contracts; DD-06 Governance Rules; DD-08 Orchestration Guards.

### TF-12 — Total Penalty Cap Enforcement
- **Given** computed penalties sum below `-35` in DEEP.
- **When** cap enforcement runs.
- **Then** penalties are capped at `-35` with deterministic item dropping order.
- **Minimal Required Inputs**: penalty list with ordered categories/reasons, `run_mode=DEEP`, cap value in `RunConfig`.
- **Traceability**: DD-05 Penalty Engine Specification; DD-07 Canonicalization Specification.

### TF-13 — Canonicalization Stability
- **Given** two logically identical inputs with different ordering.
- **When** canonicalization runs.
- **Then** canonical hash is identical.
- **And** if only `retrieval_timestamp` differs, canonical hash is identical while `snapshot_hash` for the raw input differs.
- **Minimal Required Inputs**: PortfolioSnapshot variants with reordered holdings and differing `retrieval_timestamp`.
- **Traceability**: DD-07 Canonicalization Specification.

### TF-14 — Partial Portfolio Run Threshold
- **Given** a portfolio with mixed outcomes.
- **When** failure/veto rate is computed.
- **Then**
  - if `FAILED`/`VETOED` holdings are `<=30%`, portfolio `COMPLETED`.
  - if `FAILED`/`VETOED` holdings are `>30%`, portfolio `VETOED` (unless already `FAILED`).
- **Minimal Required Inputs**: `PortfolioSnapshot` with >=10 holdings, per-holding statuses, `run_config.partial_failure_veto_threshold_pct` (default 30.0) in `RunConfig`.
- **Traceability**: DD-04 Orchestration Flow; DD-08 Orchestration Guards.

## 5. How to Use These Fixtures
5.1 Fixtures are loaded by tests (e.g., pytest) using deterministic file reads from the `fixtures/` naming convention.
5.2 Each test should load:
- the input fixture(s)
- the expected output fixture
- compare canonical hashes and run outcomes deterministically
5.3 Tests should never mutate fixture files at runtime; all modifications occur in memory and are discarded after the test run.

## 6. Acceptance Criteria
6.1 DD-09 is complete when:
- All fixture standards and metadata requirements are documented.
- All required fixture types are enumerated.
- The test matrix includes TF-01 through TF-14 with Given/When/Then and traceability.
- Deterministic timestamp and SourceRef rules are explicitly enforced.
- Portfolio-first and hard-stop precedence are explicitly stated.
