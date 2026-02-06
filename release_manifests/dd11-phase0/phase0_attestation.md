# Phase 0 Readiness Attestation (dd11-phase0)

Status: **FAILED**
Generated at (UTC): 2026-02-06T09:41:23.367757Z

## Checks
- Config bundle completeness (RunConfig, ConfigSnapshot, registries)
- Schema/contract conformance (DD-01/DD-02/DD-03)
- Hash computation + drift detection (DD-07)
- Environment parity (UTC, locale invariance, serialization invariance)
- Fixture compliance (DD-09)

## RunConfig hashes
- RunConfig_DEEP: `2d72dc15b0d2a933c2f773b17bbd0ede628e0c2f8b8b43e199d7e735c98d8c51`
- run_config: `c9cd1a32f5a7558fb3825a2035c0f5c0deec2d243541df743e1d5af6aa282a3c`

## Errors
- Multiple ConfigSnapshot files found in config: [PosixPath('config/release_bundle/ConfigSnapshot_release.json'), PosixPath('config/release_bundle/config_snapshot.json')].
- ConfigSnapshot schema validation failed for fixtures/config/ConfigSnapshot_BASE.json: 3 validation errors for ConfigSnapshot
hash
  Field required [type=missing, input_value={'rubric_version': 'IMP-0...cal_field_registry': {}}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
hard_stop_field_registry
  Extra inputs are not permitted [type=extra_forbidden, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
penalty_critical_field_registry
  Extra inputs are not permitted [type=extra_forbidden, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
- PortfolioSnapshot schema validation failed for fixtures/portfolio/PortfolioSnapshot_TF15_invalid.json: 1 validation error for PortfolioSnapshot
portfolio_id
  Field required [type=missing, input_value={'as_of_date': '2025-01-0...00:00Z', 'holdings': []}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
- Expected packet schema validation failed for fixtures/expected/TF-06_expected_penalty_breakdown.json: 11 validation errors for PortfolioCommitteePacket
run_id
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
portfolio_id
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
portfolio_run_outcome
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
category_A_missing_critical
  Extra inputs are not permitted [type=extra_forbidden, input_value=-6.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_B_staleness
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_C_contradictions_integrity
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_D_confidence
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_E_fx_exposure_risk
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_F_data_validity
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
total_penalties
  Extra inputs are not permitted [type=extra_forbidden, input_value=-6.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
details
  Extra inputs are not permitted [type=extra_forbidden, input_value=[{'category': 'A', 'reaso... 'source_agent': 'DIO'}], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
- Expected packet schema validation failed for fixtures/expected/TF-07_expected_penalty_breakdown.json: 11 validation errors for PortfolioCommitteePacket
run_id
  Field required [type=missing, input_value={'category_A_missing_crit...es': 0.0, 'details': []}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
portfolio_id
  Field required [type=missing, input_value={'category_A_missing_crit...es': 0.0, 'details': []}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
portfolio_run_outcome
  Field required [type=missing, input_value={'category_A_missing_crit...es': 0.0, 'details': []}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
category_A_missing_critical
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_B_staleness
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_C_contradictions_integrity
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_D_confidence
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_E_fx_exposure_risk
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_F_data_validity
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
total_penalties
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
details
  Extra inputs are not permitted [type=extra_forbidden, input_value=[], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
- Expected packet schema validation failed for fixtures/expected/TF-08_expected_penalty_breakdown.json: 11 validation errors for PortfolioCommitteePacket
run_id
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
portfolio_id
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
portfolio_run_outcome
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
category_A_missing_critical
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_B_staleness
  Extra inputs are not permitted [type=extra_forbidden, input_value=-5.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_C_contradictions_integrity
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_D_confidence
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_E_fx_exposure_risk
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_F_data_validity
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
total_penalties
  Extra inputs are not permitted [type=extra_forbidden, input_value=-5.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
details
  Extra inputs are not permitted [type=extra_forbidden, input_value=[{'category': 'B', 'reaso... 'source_agent': 'DIO'}], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
- Expected packet schema validation failed for fixtures/expected/TF-10_expected_penalty_breakdown.json: 11 validation errors for PortfolioCommitteePacket
run_id
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
portfolio_id
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
portfolio_run_outcome
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
category_A_missing_critical
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_B_staleness
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_C_contradictions_integrity
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_D_confidence
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_E_fx_exposure_risk
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_F_data_validity
  Extra inputs are not permitted [type=extra_forbidden, input_value=-6.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
total_penalties
  Extra inputs are not permitted [type=extra_forbidden, input_value=-6.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
details
  Extra inputs are not permitted [type=extra_forbidden, input_value=[{'category': 'F', 'reaso... 'source_agent': 'DIO'}], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
- Expected packet schema validation failed for fixtures/expected/TF-12_expected_penalty_breakdown.json: 11 validation errors for PortfolioCommitteePacket
run_id
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
portfolio_id
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
portfolio_run_outcome
  Field required [type=missing, input_value={'category_A_missing_crit...'source_agent': 'DIO'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
category_A_missing_critical
  Extra inputs are not permitted [type=extra_forbidden, input_value=-14.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_B_staleness
  Extra inputs are not permitted [type=extra_forbidden, input_value=-5.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_C_contradictions_integrity
  Extra inputs are not permitted [type=extra_forbidden, input_value=-10.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_D_confidence
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_E_fx_exposure_risk
  Extra inputs are not permitted [type=extra_forbidden, input_value=0.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
category_F_data_validity
  Extra inputs are not permitted [type=extra_forbidden, input_value=-6.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
total_penalties
  Extra inputs are not permitted [type=extra_forbidden, input_value=-35.0, input_type=float]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
details
  Extra inputs are not permitted [type=extra_forbidden, input_value=[{'category': 'A', 'reaso... 'source_agent': 'DIO'}], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
- Expected packet schema validation failed for fixtures/expected/TF-15_expected_failed_packet.json: 7 validation errors for PortfolioCommitteePacket
portfolio_id
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.12/v/string_type
as_of_date
  Extra inputs are not permitted [type=extra_forbidden, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
base_currency
  Extra inputs are not permitted [type=extra_forbidden, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
config_hashes
  Extra inputs are not permitted [type=extra_forbidden, input_value={'config_snapshot_hash': ...ig_hash': 'placeholder'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
failure_reason
  Extra inputs are not permitted [type=extra_forbidden, input_value='portfolio_snapshot_portfolio_id:Field required', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
reasons
  Extra inputs are not permitted [type=extra_forbidden, input_value=['portfolio_snapshot_portfolio_id:Field required'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
run_mode
  Extra inputs are not permitted [type=extra_forbidden, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
- Fixture fixtures/expected/TF01_happy_path_expected.json missing required metadata field 'fixture_id'.
- Fixture fixtures/expected/TF01_happy_path_expected.json missing required metadata field 'version'.
- Fixture fixtures/expected/TF01_happy_path_expected.json missing required metadata field 'description'.
- Fixture fixtures/expected/TF01_happy_path_expected.json missing required metadata field 'created_at_utc'.
- Expected packet schema validation failed for fixtures/expected/TF01_happy_path_expected.json: 1 validation error for PortfolioCommitteePacket
run_id
  Field required [type=missing, input_value={'portfolio_id': 'PORT-N3...outcome': 'COMPLETED'}]}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
- Fixture fixtures/expected/TF02_missing_base_currency_expected.json missing required metadata field 'fixture_id'.
- Fixture fixtures/expected/TF02_missing_base_currency_expected.json missing required metadata field 'version'.
- Fixture fixtures/expected/TF02_missing_base_currency_expected.json missing required metadata field 'description'.
- Fixture fixtures/expected/TF02_missing_base_currency_expected.json missing required metadata field 'created_at_utc'.
- Expected packet schema validation failed for fixtures/expected/TF02_missing_base_currency_expected.json: 2 validation errors for PortfolioCommitteePacket
run_id
  Field required [type=missing, input_value={'portfolio_id': 'PORT-N3...on': 'portfolio_vetoed'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
reason
  Extra inputs are not permitted [type=extra_forbidden, input_value='portfolio_vetoed', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
