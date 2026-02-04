# DD-05 — Penalty Engine Spec (Portfolio-First)

## 1. Purpose
The Penalty Engine is the deterministic policy layer that converts:
- missing data
- stale data
- integrity contradictions
- low confidence / uncertainty
- FX exposure issues
- data validity events (corporate actions)

into a standardized `PenaltyBreakdown` used by the Risk Officer + Chair when producing:
- `HoldingPacket.scorecard.penalty_breakdown`
- `HoldingPacket.scorecard.final_score`
- portfolio-level summaries (where applicable)

It enforces the HLD principles:
- **no invented numbers**
- **portfolio-first**
- **hard-stops beat penalties**
- **deterministic + reproducible**

---

## 2. Scope
This spec defines:
- penalty categories **A–F**
- penalty triggers and amounts
- staleness dual-threshold policy integration
- caps (per-category + total)
- ordering + determinism requirements
- unknown vs not_applicable semantics
- how penalties interact with veto/override hierarchy

Non-goals:
- scoring dimension weights (handled by scorecard rubric)
- portfolio concentration caps (PSCC)
- liquidity caps (LEFO)
- regime short-circuit (GRRA)
- technical runtime failure classification (FAILED outcomes)

---

## 3. Authority + precedence (must match HLD)
Penalty Engine outputs are advisory to the Chair, except where they participate in a Risk Officer veto decision.

**Absolute precedence order (HLD §3.2 + authority split):**
1. **DIO VETO** (hard-stop integrity/freshness/registry violations)
2. **GRRA SHORT_CIRCUIT** (do_not_trade)
3. **Risk Officer VETO** (extreme uncertainty / safety veto at holding scope)
4. **LEFO hard overrides + liquidity caps**
5. **PSCC concentration/structure caps**
6. **Risk Officer PENALTIES** (this engine: Category A–F)
7. **Chair aggregation**

**Invariants:**
- Penalties must never be applied to a holding or portfolio that is already *VETOED* by DIO (hard-stop supersedes penalty).
- If Risk Officer issues a holding-level VETO, no further penalties/caps are applied to that holding; the holding is marked VETOED and explanation is recorded.

**Acceptance Criteria:**
- DD-05 explicitly separates Risk Officer VETO from Risk Officer PENALTIES in precedence.
- DD-05 precedence is consistent with HLD authority model and cannot be interpreted ambiguously.

---

## 4. Inputs and outputs (contracts)

### 4.1 Inputs
Penalty Engine consumes existing HLD outputs/structures (no new required schema types).

**Required sources:**
- `RunConfig`
  - `run_mode` (FAST | DEEP)
  - `burn_rate_classification` map
  - `staleness_thresholds` (mode defaults)
  - `penalty_caps` (mode defaults)
- `ConfigSnapshot`
  - `hard_stop_field_registry`
  - `penalty_critical_field_registry`
- `DIOOutput`
  - `staleness_flags`
  - `missing_hard_stop_fields`
  - `missing_penalty_critical_fields`
  - `contradictions`
  - `unsourced_numbers_detected`
  - `corporate_action_risk`
- Collection of `AgentResult` objects
  - `confidence`
  - `suggested_penalties` (optional input signals, but final penalty rules must be standardized here)

### 4.2 Output
Penalty Engine produces a `PenaltyBreakdown` per holding (HLD §5.1 / §7.4).

**PenaltyBreakdown fields (authoritative):**
- `category_A_missing_critical` (0..-20)
- `category_B_staleness` (0..-10)
- `category_C_contradictions_integrity` (0..-20)
- `category_D_confidence` (0..-10)
- `category_E_fx_exposure_risk` (0..-10)
- `category_F_data_validity` (0..-10)
- `total_penalties` (capped: -35 DEEP, -40 FAST)
- `details`: list of `PenaltyItem`

**PenaltyItem fields (authoritative):**
- `category`: "A" | "B" | "C" | "D" | "E" | "F"
- `reason`: string
- `amount`: float (negative)
- `source_agent`: string

---

## 5. Category definitions (must match HLD §7.4)
**Category A — Missing Critical Data**  
Missing fields in `PenaltyCriticalFieldRegistry` (NOT hard-stop fields).

**Category B — Staleness**  
Data older than penalty thresholds but not beyond hard-stop thresholds.

**Category C — Contradictions / Integrity**  
Unresolved contradictions, integrity failures, unsourced-number events.

**Category D — Confidence / Uncertainty**  
Low-confidence situations (including Devil’s Advocate unresolved fatal risk).

**Category E — FX Exposure Risk**  
FX missing/stale/overexposure issues when currency != base_currency.

**Category F — Data Validity**  
Corporate actions and data comparability risks (R17 update).

---

## 6. Core invariants (do not violate)

### 6.1 Hard-stop supersedes penalty
If DIO indicates a hard-stop condition (holding-level or portfolio-level), penalties must not be applied to “save” the run.

Examples:
- staleness hard-stop triggered ⇒ holding_run_outcome = VETOED (no Category B penalty)
- missing hard-stop field ⇒ holding_run_outcome = VETOED (no Category A penalty)

### 6.2 Unknown vs not_applicable semantics (HLD §7.6)
A MetricValue is:
- **Unknown** if `value=None` with `missing_reason` and `not_applicable=false` → can incur penalties
- **Not applicable** if `not_applicable=true` → must incur **no penalty** for that field

Schema violation:
- `value=None` AND `missing_reason=None` AND `not_applicable=false` ⇒ technical failure risk (typically FAILED, not penalty-driven)

### 6.3 Deterministic ordering (HLD R16)
Penalty output must be stable and reproducible:
- `PenaltyBreakdown.details` sorted by:
  1) `category` (A,B,C,D,E,F)
  2) `reason` (lexicographic)
  3) `source_agent` (lexicographic)

---

## 7. Amounts, caps, and mode defaults (HLD §7.4)

### 7.1 Per-category caps (authoritative)
- Category A cap: **-20**
- Category B cap: **-10**
- Category C cap: **-20**
- Category D cap: **-10**
- Category E cap: **-10**
- Category F cap: **-10**

### 7.2 Total cap (authoritative)
- **DEEP:** total_penalty_cap = **-35**
- **FAST:** total_penalty_cap = **-40**

### 7.3 Cap enforcement order (authoritative)
1) Apply *individual* category caps first
2) Sum categories
3) Apply total cap (mode-dependent)

---

## 8. Standard penalty rules (authoritative mapping)
These are the default rules. Implementations may add more detail, but must not change these values without a version bump in `scoring_rubric_version`.

### 8.1 Category A — Missing Critical Data (0..-20)
Trigger source: `DIOOutput.missing_penalty_critical_fields` plus instrument-type semantics from `RunConfig.burn_rate_classification`.

**Default penalty items:**
- Missing `cash` OR `runway_months` (only when burn_rate_classification says penalty-critical): **-6**
- Missing `shares_outstanding` OR `market_cap`: **-5**
- Missing `fully_diluted_shares`: **-4**
- Missing `adv_usd` OR liquidity measure: **-5**
- Missing `price` OR `volume`: **-4**
- Missing macro input (e.g., `vix` / proxy): **-4**

**Required reason strings (stable):**
- "missing_cash_or_runway"
- "missing_shares_or_market_cap"
- "missing_fully_diluted_shares"
- "missing_liquidity_measure"
- "missing_price_or_volume"
- "missing_macro_regime_input"

**Notes:**
- If `not_applicable=true` for a field → do not penalize.
- If the holding is classified `is_burn_rate_company=true` and cash/runway/burn is missing, that is a hard-stop registry failure handled by DIO, not Category A.

### 8.2 Category B — Staleness (0..-10)
Trigger source: `DIOOutput.staleness_flags` where:
- `hard_stop_triggered=false`
- age exceeds penalty threshold

**Default penalty items:**
- Financials stale (FAST >120d, DEEP >90d): **-5**
- Price/Volume stale (FAST >3d, DEEP >1d): **-3**
- Company updates stale (FAST >90d, DEEP >60d): **-2**
- Macro/regime stale (FAST >14d, DEEP >7d): **-4**

**Required reason strings (stable):**
- "stale_financials"
- "stale_price_volume"
- "stale_company_updates"
- "stale_macro_regime"

**Invariant:**
- If data is beyond hard-stop threshold, DIO vetoes. Category B must not be applied.

### 8.3 Category C — Contradictions / Integrity (0..-20)
Trigger sources:
- `DIOOutput.contradictions`
- `DIOOutput.unsourced_numbers_detected`

**Default penalty items:**
- Contradiction in critical metric detected: **-10**
- Conflicting sources unresolved: **-6** (only if there is an explicit “unresolved” marker in contradiction resolution)
- Unsourced numbers detected in any agent output: **-10** AND must set DIO veto flag upstream (integrity_veto_triggered)

**Required reason strings (stable):**
- "contradiction_detected"
- "conflict_unresolved"
- "unsourced_numbers_detected"

**Notes:**
- If `unsourced_numbers_detected=true`, the expected outcome is typically holding VETOED by DIO (integrity). If the system chooses to proceed (debug mode), still apply the penalty item and log explicit limitation.

### 8.4 Category D — Confidence / Uncertainty (0..-10)
Trigger sources:
- count of agents with `confidence < 0.5`
- Devil’s Advocate unresolved fatal risk flag (via AgentResult.veto_flags or suggested_penalties marker)

**Default penalty items:**
- ≥3 agents confidence <0.5: **-5**
- Devil’s Advocate raises unresolved fatal risk: **-5**

**Required reason strings (stable):**
- "low_confidence_multi_agent"
- "devils_advocate_unresolved_fatal_risk"

### 8.5 Category E — FX Exposure Risk (0..-10)
Trigger sources:
- instrument currency vs `PortfolioConfig.base_currency`
- FX rate availability and staleness (from DIO portfolio checks)
- PSCC aggregated FX exposure threshold

**Default penalty items:**
- FX rate missing when currency != base_currency: **-5**
- FX rate stale beyond penalty threshold but within hard-stop: **-3**
- FX exposure >20% portfolio without hedging data: **-5**

**Required reason strings (stable):**
- "fx_rate_missing"
- "fx_rate_stale"
- "fx_exposure_high_no_hedge_data"

**Invariant:**
- FX beyond hard-stop threshold (FAST >7d, DEEP >48h) is a **portfolio-level DIO veto**, not Category E.

### 8.6 Category F — Data Validity (0..-10) (R17 update)
Trigger sources:
- `DIOOutput.corporate_action_risk`
- explicit source reliability flags (if present)

**Default penalty items:**
- Recent split/reverse split detected within 90 days: **-6**
- Recent dividend/distribution affecting comparisons: **-3**
- Spinoff/merger affecting structure: **-8**
- Data source reliability flagged low: **-5**

**Required reason strings (stable):**
- "recent_split_or_reverse_split"
- "recent_dividend_or_distribution"
- "recent_spinoff_or_merger"
- "low_source_reliability"

**Invariant:**
- Corporate actions are **Category F**, never Category B.

---

## 9. Computation algorithm (deterministic)

Given `holding_id`:

### Step 0 — Do not compute if hard-stopped
If holding_run_outcome is already `VETOED` due to:
- missing hard-stop fields
- hard-stop staleness
- integrity veto
then return a `PenaltyBreakdown` with:
- all categories = 0
- total_penalties = 0
- details = []
and rely on the veto note/limitations to explain.

(Reason: hard-stop supersedes penalties.)

### Step 1 — Build candidate penalty items
Create a working list `items[]` of PenaltyItems from §§8.1–8.6.

### Step 2 — Deduplicate identical penalty items
Two penalty items are duplicates if:
- same category
- same reason
- same source_agent
Keep only one instance.

### Step 3 — Apply per-category caps
Sum by category and cap to that category’s max negative.

Example:
- Category A computed -23 ⇒ set Category A = -20 and drop the lowest-priority A-items (priority ordering in Step 4).

### Step 4 — Priority ordering inside a category (tie-breaker)
If cap forces dropping items, drop in this order (lowest priority first):
- within same category: drop smallest magnitude first
- if equal magnitude: drop lexicographically later `reason`

(Goal: preserve the most important penalties deterministically.)

### Step 5 — Apply total cap
Sum all category totals. If below (more negative than) total cap:
- scale by dropping lowest-priority items across all categories using ordering:
  1) smaller magnitude first
  2) category later in alphabet first (F before E before D…)
  3) lexicographically later reason
until total meets cap.

### Step 6 — Finalize sorting
Sort `details` per §6.3 for canonical stability.

### Step 7 — Output
Return `PenaltyBreakdown` with:
- per-category totals
- total_penalties
- details (sorted)

---

## 10. Interaction with outcomes and recommendations
Penalty Engine does not set outcomes directly, but its results support Risk Officer logic.

**Typical policy patterns:**
- If penalties approach total cap AND multi-agent confidence is low, Risk Officer may veto (HLD §7.4 “extreme uncertainty”).
- Chair computes:
  - `FinalScore = clamp(BaseScore - TotalPenalties, 0, 100)`
- Hard overrides still apply after score:
  - LEFO liquidity grade ≤1 → avoid/cap regardless of final score
  - PSCC breaches → cap/downgrade regardless of final score

---

## 11. Test vectors (must align to HLD tests)

### TV1 — Burn-rate classification (HLD I9)
Holding B: is_burn_rate_company=false, not_applicable=false, missing cash/runway  
Expected: Category A includes `missing_cash_or_runway = -6`

Holding C: not_applicable=true, missing cash/runway  
Expected: no Category A penalty for cash/runway

Holding A: is_burn_rate_company=true, missing cash  
Expected: holding VETOED by DIO; penalty engine returns zeros (hard-stop supersedes)

### TV2 — Staleness dual threshold (HLD I10)
DEEP mode:
- financials age 100d (penalty threshold 90d, hard-stop 180d)  
Expected: Category B includes `stale_financials = -5`

- financials age 200d (beyond hard-stop)  
Expected: DIO veto; penalty engine returns zeros

### TV3 — Corporate action Category F (HLD I11)
Split 60 days ago  
Expected: Category F includes `recent_split_or_reverse_split = -6` (NOT Category B)

### TV4 — Total cap enforcement
DEEP: computed totals = -42  
Expected: total_penalties == -35 and details dropped deterministically

### TV5 — Deterministic ordering (HLD R16)
Same inputs with different item insertion order  
Expected: identical `PenaltyBreakdown.details` ordering + identical totals

---

## 12. Versioning
This penalty policy is versioned via:
- `ConfigSnapshot.scoring_rubric_version` (e.g., "v1.0")
- changes to penalty amounts, caps, or reason strings require a version bump

---
