from __future__ import annotations

import json
from pathlib import Path

from src.core.guards.guards_g0_g10 import G7DeterminismGuard, GuardContext
from src.core.models import ConfigSnapshot, PortfolioConfig, PortfolioSnapshot, RunConfig, RunOutcome


def _load_fixture(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("payload", payload)


def test_determinism_guard_flags_ordering_violation() -> None:
    snapshot_data = _load_fixture("fixtures/portfolio/PortfolioSnapshot_N3.json")
    snapshot_data = {**snapshot_data, "holdings": list(reversed(snapshot_data["holdings"]))}
    config_snapshot = _load_fixture("fixtures/config/ConfigSnapshot_v1.json")
    seeded = _load_fixture("fixtures/seeded/SeededData_HappyPath.json")
    config_snapshot = {
        **config_snapshot,
        "registries": {
            **config_snapshot["registries"],
            **seeded,
        },
    }

    snapshot = PortfolioSnapshot.parse_obj(snapshot_data)
    context = GuardContext(
        portfolio_snapshot=snapshot,
        portfolio_config=PortfolioConfig.parse_obj(_load_fixture("fixtures/portfolio_config.json")),
        run_config=RunConfig.parse_obj(_load_fixture("fixtures/config/RunConfig_DEEP.json")),
        config_snapshot=ConfigSnapshot.parse_obj(config_snapshot),
        manifest=None,
        config_hashes={"run_config_hash": "placeholder", "config_snapshot_hash": "placeholder"},
        ordered_holdings=list(snapshot.holdings),
        agent_results=[],
        portfolio_outcome=RunOutcome.COMPLETED,
    )

    guard = G7DeterminismGuard()
    evaluation = guard.evaluate(context=context)

    assert evaluation.result.status == "failed"
    assert "determinism_order_violation" in evaluation.result.reasons
