from __future__ import annotations

from pathlib import Path

import pytest

from src.testing.replay import BundlePaths, FixturePaths, run_fixture


def test_run_fixture_requires_config_paths(tmp_path: Path) -> None:
    fixture_paths = FixturePaths(
        portfolio_snapshot=tmp_path / "missing_snapshot.json",
        portfolio_config=tmp_path / "missing_config.json",
        seeded=tmp_path / "missing_seeded.json",
    )

    with pytest.raises(ValueError, match="RunConfig and ConfigSnapshot"):
        run_fixture(fixture_paths, BundlePaths())
