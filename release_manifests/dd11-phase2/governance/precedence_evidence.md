# Governance Precedence Evidence (DD-11 Phase 2)

## Test Evidence
- Source: tests/governance/test_precedence_order.py
- Execution log: release_manifests/dd11-phase2/governance/pytest_governance.txt

## Assertions Covered
- DIO veto blocks execution immediately (portfolio veto stops scoring/caps, no holding packets).
- GRRA short-circuit bypasses downstream agents (short-circuited holdings, no scorecards).
- Risk Officer veto overrides penalties (vetoed holding has no scorecard).
- LEFO caps precede PSCC caps and penalties (cap order validated with scorecard base + penalties).
- PSCC caps precede penalties (validated in caps/penalty sequencing test).

## Chair Aggregation Order
- Chair aggregation (portfolio committee packet assembly) occurs after governance evaluation and holding processing via `Orchestrator._emit_packets` calling `build_portfolio_packet`, which is invoked after governance decision and holding states are finalized in `Orchestrator.run`.
