# IMP-05 — Agent Enablement

## Enabled Agents and Order

Tier 1 (governance-first, deterministic execution order):
1. DIO (portfolio scope first, then holding scope)
2. GRRA (portfolio scope)
3. LEFO (holding scope)
4. PSCC (portfolio scope)
5. Risk Officer (holding scope)

Tier 2 (advisory analysis, holding scope):
6. Fundamentals
7. Technical
8. Devil’s Advocate

Notes:
- DIO portfolio veto stops downstream agents for the portfolio.
- GRRA do-not-trade short-circuits downstream agents for the portfolio.
- Holding-level DIO veto (including unsourced numbers) stops downstream agents for that holding.
- Holdings already terminal from guard violations are skipped for downstream agents.

## AgentResult Minimal Contract (Current Outputs)

All agents emit the canonical AgentResult envelope with strict conformance checks:
- `agent_name`, `scope`, `status`, `confidence`
- `key_findings` (agent-specific)
- `metrics` (MetricValue list)
- `suggested_penalties`
- `veto_flags`
- Optional `counter_case`, `notes`, and `holding_id`

Minimal key_findings by agent:
- **DIO:** `missing_hard_stop_fields`, `missing_penalty_critical_fields`, `staleness_flags`, `contradictions`, `unsourced_numbers_detected`, `corporate_action_risk`
- **GRRA:** `regime_label`, `regime_confidence`, `do_not_trade_flag`
- **LEFO:** `liquidity_grade`, `hard_override_triggered`, optional cap fields
- **PSCC:** `concentration_breaches`, `position_caps_applied`, `fx_exposure_by_currency`, `portfolio_liquidity_risk`
- **Risk Officer:** `risk_summary`, `veto_recommended`
- **Fundamentals:** `fundamental_metrics`
- **Technical:** `technical_signals`
- **Devil’s Advocate:** `risk_flags`, `unresolved_fatal_risk`, `narrative_limitations`, optional `counter_case`

## G5 Conformance Enforcement

- G5 validates each AgentResult against the canonical schema and enforces:
  - Required envelope fields
  - Status and confidence constraints
  - Scope/holding_id requirements
- Invalid holding-scope AgentResult → holding FAILED.
- Invalid portfolio-scope AgentResult → run FAILED.

## Test Mapping

- **AgentResult conformance guard (G5):** `test_agent_result_conformance_guard_fails_holding`, `test_agent_result_conformance_guard_marks_holding_failed`
- **DIO veto stops downstream:** `test_dio_veto_stops_downstream_for_holding`
- **GRRA short-circuit:** `test_grra_short_circuit_blocks_non_governance_agents`
- **Deterministic agent ordering:** `test_agent_ordering_is_deterministic`
