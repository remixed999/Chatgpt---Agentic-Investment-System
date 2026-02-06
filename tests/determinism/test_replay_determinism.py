from __future__ import annotations

from pathlib import Path

from src.testing.replay import BundlePaths, FixturePaths, replay_n_times


def test_replay_determinism_tf01() -> None:
    fixture_paths = FixturePaths(
        portfolio_snapshot=Path("fixtures/portfolio/PortfolioSnapshot_N3.json"),
        portfolio_config=Path("fixtures/portfolio_config.json"),
        seeded=Path("fixtures/seeded/SeededData_HappyPath.json"),
        run_config=Path("fixtures/config/RunConfig_DEEP.json"),
        config_snapshot=Path("fixtures/config/ConfigSnapshot_v1.json"),
    )
    results = replay_n_times(
        "TF-01",
        2,
        fixture_paths=fixture_paths,
        bundle_paths=BundlePaths(),
    )

    assert results[0].hashes["decision_hash"] == results[1].hashes["decision_hash"]
    assert results[0].outcomes == results[1].outcomes
