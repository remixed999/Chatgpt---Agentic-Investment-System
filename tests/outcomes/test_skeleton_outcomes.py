from __future__ import annotations

import json
from pathlib import Path

from src.core.orchestration import Orchestrator
from src.schemas.models import PortfolioCommitteePacket, PortfolioRunOutcome


def _load_payload(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("payload", data)


def test_tf01_happy_path_completed() -> None:
    result = Orchestrator().run(
        portfolio_snapshot_data=_load_payload("fixtures/portfolio/PortfolioSnapshot_N3.json"),
        portfolio_config_data=_load_payload("fixtures/config/PortfolioConfig_BASE.json"),
        run_config_data=_load_payload("fixtures/config/RunConfig_DEEP.json"),
        config_snapshot_data=_load_payload("fixtures/config/ConfigSnapshot_BASE.json"),
    )

    expected = _load_payload("fixtures/expected/TF01_happy_path_expected.json")
    packet = result.packet

    assert isinstance(packet, PortfolioCommitteePacket)
    assert packet.portfolio_run_outcome == PortfolioRunOutcome.COMPLETED
    assert packet.portfolio_id == expected["portfolio_id"]
    assert [holding.holding_run_outcome.value for holding in packet.holdings] == [
        holding["holding_run_outcome"] for holding in expected["holdings"]
    ]


def test_tf02_missing_base_currency_vetoed() -> None:
    result = Orchestrator().run(
        portfolio_snapshot_data=_load_payload("fixtures/portfolio/PortfolioSnapshot_missing_base_currency.json"),
        portfolio_config_data={"base_currency": None},
        run_config_data=_load_payload("fixtures/config/RunConfig_DEEP.json"),
        config_snapshot_data=_load_payload("fixtures/config/ConfigSnapshot_BASE.json"),
    )

    expected = _load_payload("fixtures/expected/TF02_missing_base_currency_expected.json")
    packet = result.packet

    assert packet.portfolio_id == expected["portfolio_id"]
    assert packet.portfolio_run_outcome.value == expected["portfolio_run_outcome"]


def test_tf04_identity_missing_holding_failed() -> None:
    result = Orchestrator().run(
        portfolio_snapshot_data=_load_payload("fixtures/portfolio/PortfolioSnapshot_TF04_identity_missing.json"),
        portfolio_config_data=_load_payload("fixtures/config/PortfolioConfig_BASE.json"),
        run_config_data={"run_mode": "FAST", "partial_failure_veto_threshold_pct": 60.0},
        config_snapshot_data=_load_payload("fixtures/config/ConfigSnapshot_BASE.json"),
    )

    packet = result.packet

    assert packet.portfolio_run_outcome == PortfolioRunOutcome.COMPLETED
    failed = [holding for holding in packet.holdings if holding.holding_run_outcome.value == "FAILED"]
    assert failed
