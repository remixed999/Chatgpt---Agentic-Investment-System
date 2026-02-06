# DD-11 Phase 2 Acceptance Checklist (Integration Environment)

## Entry Preconditions
- [ ] Phase 0 passed, Phase 1 passed, hashes unchanged. (FAIL: release_manifest hash mismatch)

## Integration Environment Parity
- [x] UTC timezone enforced. (PASS)
- [x] Locale-invariant numeric serialization confirmed. (PASS)
- [x] Serialization parity confirmed. (PASS)

## Full Orchestration Execution
- [x] Full orchestration executed with no stubs. (PASS)

## Deterministic Replay (Hard Gate)
- [x] Two independent runs, zero diff. (PASS)

## Governance Precedence Enforcement
- [x] DIO veto blocks execution immediately. (PASS)
- [x] GRRA short-circuit bypasses downstream agents. (PASS)
- [x] Risk Officer veto overrides penalties. (PASS)
- [x] LEFO caps precede PSCC caps. (PASS)
- [x] PSCC caps precede penalties. (PASS)
- [x] Chair aggregation occurs last. (PASS)

## Guard Enforcement
- [x] G0 schema/intake enforcement. (PASS)
- [x] G2 provenance enforcement. (PASS)
- [x] G5 AgentResult conformance enforcement. (PASS)
- [x] G7 determinism/ordering enforcement. (PASS)
- [x] G9 partial portfolio failure threshold enforcement. (PASS)
- [x] G10 emission eligibility enforcement. (PASS)

## Canonicalization & Hashing Rules
- [x] Canonical JSON serialization applied. (PASS)
- [x] Hashes emitted only for COMPLETED outcomes. (PASS)
- [x] Hash inputs exclude non-decision fields. (PASS)
- [x] Hashes stable across replay. (PASS)

## Packet Schema Validation
- [x] PortfolioCommitteePacket validated. (PASS)
- [x] HoldingPacket validated. (PASS)
- [x] FailedRunPacket validated when emitted. (PASS: not emitted in completed run)

## Test Execution & Coverage
- [ ] Integration-relevant tests executed with no determinism/governance skips. (FAIL: determinism/canonicalization/governance tests skipped)

## Evidence Completeness
- [x] All Phase 2 artifacts captured. (PASS)
