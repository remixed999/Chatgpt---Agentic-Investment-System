# Phase 0 Readiness Attestation (dd11-phase0)

Status: **FAILED**
Generated at (UTC): 2026-02-06T10:18:52.702127Z

## Checks
- Config bundle completeness (RunConfig, ConfigSnapshot, registries)
- Schema/contract conformance (DD-01/DD-02/DD-03)
- Hash computation + drift detection (DD-07)
- Environment parity (UTC, locale invariance, serialization invariance)
- Fixture compliance (DD-09)

## RunConfig hashes
- RunConfig_DEEP: `2d72dc15b0d2a933c2f773b17bbd0ede628e0c2f8b8b43e199d7e735c98d8c51`
- run_config: `c9cd1a32f5a7558fb3825a2035c0f5c0deec2d243541df743e1d5af6aa282a3c`

ConfigSnapshot hash: `25978da3272b55fe7ca2895310a4ab0e60a573cc392259892504d7d5f9e197f0`

## Errors
- ConfigSnapshot schema validation failed for config/release_bundle/config_snapshot.json: 3 validation errors for ConfigSnapshot
hash
  Field required [type=missing, input_value={'rubric_version': 'IMP-0...cal_field_registry': {}}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
hard_stop_field_registry
  Extra inputs are not permitted [type=extra_forbidden, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
penalty_critical_field_registry
  Extra inputs are not permitted [type=extra_forbidden, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
- ConfigSnapshot missing required registry 'hard_stop_field_registry'.
- ConfigSnapshot missing required registry 'penalty_critical_field_registry'.
