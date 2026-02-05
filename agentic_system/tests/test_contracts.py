from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agentic_system.config.loader import compute_hash, load_config_snapshot, load_run_config
from agentic_system.schemas.contracts import AgentResult, MetricValue, SourceRef


# DD-10: Phase 0/1 blocking tests

def _run_config_payload() -> dict:
    return {
        "run_mode": "FAST",
        "burn_rate_classification": {"H1": {"is_burn_rate_company": True}},
        "staleness_thresholds": {
            "financials_penalty_max_age_days": 120,
            "financials_hard_stop_max_age_days": 365,
            "price_volume_penalty_max_age_days": 3,
            "price_volume_hard_stop_max_age_days": 30,
            "company_updates_penalty_max_age_days": 90,
            "macro_regime_penalty_max_age_days": 14,
            "macro_regime_hard_stop_max_age_days": 90,
            "fx_rate_hard_stop_max_age_days": 7,
        },
        "penalty_caps": {
            "total_penalty_cap": -40.0,
            "category_A_cap": -20.0,
            "category_B_cap": -10.0,
            "category_C_cap": -20.0,
            "category_D_cap": -10.0,
            "category_E_cap": -10.0,
            "category_F_cap": -10.0,
        },
        "custom_overrides": {"debug": True},
    }


def _config_snapshot_payload() -> dict:
    return {
        "hard_stop_field_registry": {
            "identity_fields_all_companies": ["ticker", "exchange", "currency"],
            "burn_rate_fields_conditional": ["cash", "runway_months", "burn_rate"],
            "portfolio_level_fields": ["base_currency"],
        },
        "penalty_critical_field_registry": {
            "fundamentals": [
                "shares_outstanding",
                "fully_diluted_shares",
                "market_cap",
                "revenue",
                "earnings",
                "total_debt",
                "shareholders_equity",
            ],
            "fundamentals_conditional_burn_rate": ["cash", "runway_months", "burn_rate"],
            "technicals": ["price", "volume", "52w_high", "52w_low", "beta"],
            "liquidity": ["adv_usd", "bid_ask_spread_bps"],
            "macro_regime": ["regime_label", "vix", "credit_spreads", "market_breadth"],
        },
        "scoring_rubric_version": "v1.0",
        "agent_prompt_versions": {"DIO": "v1.0"},
    }


def test_schema_validation() -> None:
    source = SourceRef(
        as_of_date=datetime.now(timezone.utc),
        retrieval_timestamp=datetime.now(timezone.utc),
        origin="manual_paste",
    )
    metric = MetricValue(value=1.0, source_ref=source)
    AgentResult(
        agent_name="DIO",
        status="completed",
        confidence=0.9,
        key_findings={"notes": "ok"},
        metrics=(metric,),
        suggested_penalties=(),
        veto_flags=(),
    )
    with pytest.raises(ValueError):
        MetricValue(value=2.0)


def test_config_loading(tmp_path: Path) -> None:
    run_config_path = tmp_path / "run_config.json"
    config_snapshot_path = tmp_path / "config_snapshot.json"
    run_config_path.write_text(json.dumps(_run_config_payload()), encoding="utf-8")
    config_snapshot_path.write_text(
        json.dumps(_config_snapshot_payload()), encoding="utf-8"
    )
    run_config = load_run_config(run_config_path)
    config_snapshot = load_config_snapshot(config_snapshot_path)
    assert run_config.run_mode == "FAST"
    assert config_snapshot.scoring_rubric_version == "v1.0"


def test_hash_determinism() -> None:
    payload_one = _run_config_payload()
    payload_two = {
        "penalty_caps": payload_one["penalty_caps"],
        "staleness_thresholds": payload_one["staleness_thresholds"],
        "burn_rate_classification": payload_one["burn_rate_classification"],
        "run_mode": payload_one["run_mode"],
        "custom_overrides": payload_one["custom_overrides"],
    }
    hash_one = compute_hash(payload_one)
    hash_two = compute_hash(payload_two)
    assert hash_one == hash_two


def test_missing_config_hard_failure(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        load_run_config(missing_path)
