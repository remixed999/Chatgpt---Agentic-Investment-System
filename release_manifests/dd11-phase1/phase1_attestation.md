Phase name: DD-11 Phase 1
Status: FAILED
Reasons:
- pytest failed with unrecognized arguments for json reporting (see release_manifests/dd11-phase1/tests/pytest_report.txt)
Evidence files:
- release_manifests/dd11-phase1/phase0_reference/phase0_attestation.md
- release_manifests/dd11-phase1/environment/python_version.txt
- release_manifests/dd11-phase1/environment/platform.txt
- release_manifests/dd11-phase1/environment/locale_utc_check.txt
- release_manifests/dd11-phase1/tests/pytest_report.txt
- release_manifests/dd11-phase1/tests/pytest_report.json
- release_manifests/dd11-phase1/determinism/replay_run_A/runlog.json
- release_manifests/dd11-phase1/determinism/replay_run_A/output_packet.json
- release_manifests/dd11-phase1/determinism/replay_run_A/hashes.json
- release_manifests/dd11-phase1/determinism/replay_run_B/runlog.json
- release_manifests/dd11-phase1/determinism/replay_run_B/output_packet.json
- release_manifests/dd11-phase1/determinism/replay_run_B/hashes.json
- release_manifests/dd11-phase1/determinism/replay_diff.txt
- release_manifests/dd11-phase1/manifests/phase1_run_manifest.json
Determinism verdict: PASSED (replay diff empty)
