from __future__ import annotations

import json
from pathlib import Path

from src.core.models import ConfigSnapshot, PortfolioConfig, RunConfig
from src.core.penalties import DIOOutput
from src.core.penalties.penalty_engine import compute_penalty_breakdown, compute_penalty_breakdown_with_cap_tracking


def _load_payload(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("payload", payload)


def _base_config_snapshot() -> ConfigSnapshot:
    return ConfigSnapshot.parse_obj(_load_payload("fixtures/config/ConfigSnapshot_v1.json"))


def _base_run_config() -> RunConfig:
    return RunConfig.parse_obj(_load_payload("fixtures/config/RunConfig_DEEP.json"))


def _base_portfolio_config() -> PortfolioConfig:
    return PortfolioConfig.parse_obj(_load_payload("fixtures/portfolio_config.json"))


def _assert_breakdown_matches(seed_path: str, expected_path: str) -> None:
    seed = _load_payload(seed_path)
    expected = _load_payload(expected_path)
    breakdown = compute_penalty_breakdown(
        holding_id=seed["holding_id"],
        run_config=_base_run_config(),
        config_snapshot=_base_config_snapshot(),
        dio_output=DIOOutput.parse_obj(seed["dio_output"]),
        agent_results=[],
        portfolio_config=_base_portfolio_config(),
    )

    assert breakdown.model_dump() == expected


def test_tf06_non_burn_rate_missing_cash_penalty_fixture():
    _assert_breakdown_matches(
        "fixtures/seeded/TF-06_missing_cash_non_burn_rate.json",
        "fixtures/expected/TF-06_expected_penalty_breakdown.json",
    )


def test_tf07_not_applicable_cash_runway_fixture():
    _assert_breakdown_matches(
        "fixtures/seeded/TF-07_not_applicable_cash_runway.json",
        "fixtures/expected/TF-07_expected_penalty_breakdown.json",
    )


def test_tf08_staleness_penalty_fixture():
    _assert_breakdown_matches(
        "fixtures/seeded/TF-08_staleness_financials_penalty.json",
        "fixtures/expected/TF-08_expected_penalty_breakdown.json",
    )


def test_tf10_corporate_action_split_fixture():
    _assert_breakdown_matches(
        "fixtures/seeded/TF-10_corporate_action_split.json",
        "fixtures/expected/TF-10_expected_penalty_breakdown.json",
    )


def test_tf12_total_penalty_cap_fixture():
    seed = _load_payload("fixtures/seeded/TF-12_penalty_cap_enforcement.json")
    expected = _load_payload("fixtures/expected/TF-12_expected_penalty_breakdown.json")
    breakdown, cap_applied = compute_penalty_breakdown_with_cap_tracking(
        holding_id=seed["holding_id"],
        run_config=_base_run_config(),
        config_snapshot=_base_config_snapshot(),
        dio_output=DIOOutput.parse_obj(seed["dio_output"]),
        agent_results=[],
        portfolio_config=_base_portfolio_config(),
    )

    assert cap_applied is True
    assert breakdown.model_dump() == expected
