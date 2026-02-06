# DD-11 Phase 2 Attestation (Integration Environment)

- Timestamp (UTC): 2026-02-06T18:46:03Z
- Phase: DD-11 Phase 2 — Integration Environment
- Status: FAILED

## Checklist Results
- Entry Preconditions: FAIL (release manifest hash mismatch).
- Integration Environment Parity: PASS.
- Full Orchestration Execution: PASS.
- Deterministic Replay: PASS.
- Governance Precedence Enforcement: PASS.
- Guard Enforcement: PASS.
- Canonicalization & Hashing Rules: PASS.
- Packet Schema Validation: PASS (FailedRunPacket not emitted for completed outcome).
- Test Execution & Coverage: FAIL (determinism/canonicalization/governance suites skipped).
- Evidence Completeness: PASS.

## Failure Reasons
1. Release manifest hash mismatch for run_config/config_snapshot (entry precondition failure).
2. Forbidden runtime pattern scan detected datetime.now/time.time usage in tooling.
3. Integration-relevant test suites included skipped determinism/canonicalization/governance tests.

## Evidence References
- Checklist: release_manifests/dd11-phase2/checklist.md
- Entry Preconditions: release_manifests/dd11-phase2/environment/entry_preconditions.json
- Environment Parity: release_manifests/dd11-phase2/environment/environment_parity.txt
- Forbidden Runtime Scan: release_manifests/dd11-phase2/environment/forbidden_runtime_scan.txt
- Full Run Logs: release_manifests/dd11-phase2/runs/full_run/
- Determinism Replay: release_manifests/dd11-phase2/determinism/
- Governance Evidence: release_manifests/dd11-phase2/governance/
- Guard Evidence: release_manifests/dd11-phase2/guards/guard_enforcement.json
- Canonicalization Evidence: release_manifests/dd11-phase2/canonicalization/
- Packet Validation: release_manifests/dd11-phase2/outputs/packet_validation.json
- Tests: release_manifests/dd11-phase2/tests/
