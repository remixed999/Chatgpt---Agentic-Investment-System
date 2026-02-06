from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.models import AgentResult, ConfigSnapshot, PortfolioConfig, PortfolioSnapshot, RunConfig


def _load_fixture(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("payload", payload)


def test_schema_contracts_accept_fixtures() -> None:
    snapshot = PortfolioSnapshot.parse_obj(_load_fixture("fixtures/portfolio/PortfolioSnapshot_N3.json"))
    config = PortfolioConfig.parse_obj(_load_fixture("fixtures/portfolio_config.json"))
    run_config = RunConfig.parse_obj(_load_fixture("fixtures/config/RunConfig_DEEP.json"))
    config_snapshot = ConfigSnapshot.parse_obj(_load_fixture("fixtures/config/ConfigSnapshot_v1.json"))

    assert snapshot.portfolio_id == "PORT-N3"
    assert config.base_currency == "USD"
    assert run_config.run_mode.value == "DEEP"
    assert config_snapshot.rubric_version == "v1.0"


def test_agent_result_contract_requires_scope() -> None:
    with pytest.raises(Exception):
        AgentResult.parse_obj(
            {
                "agent_name": "DIO",
                "status": "completed",
                "confidence": 1.0,
                "key_findings": {},
                "metrics": [],
                "suggested_penalties": [],
                "veto_flags": [],
            }
        )

    result = AgentResult.parse_obj(
        {
            "agent_name": "DIO",
            "scope": "portfolio",
            "status": "completed",
            "confidence": 1.0,
            "key_findings": {},
            "metrics": [],
            "suggested_penalties": [],
            "veto_flags": [],
        }
    )

    assert result.scope == "portfolio"
