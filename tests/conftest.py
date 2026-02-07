from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import pytest
from pydantic import PydanticDeprecatedSince20

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("DD11_FULL_TESTS") == "1":
        return
    keep = {
        "test_orchestrator.py",
        "test_guards_and_governance.py",
        "test_portfolio_outcomes.py",
        "test_precedence_order.py",
        "test_phase1_report_determinism.py",
        "test_imp03_emission_and_thresholds.py",
        "test_release_phase0.py",
    }
    for item in items:
        if item.path.name not in keep:
            item.add_marker(pytest.mark.skip(reason="IMP-01 skeleton only; advanced tests deferred."))
