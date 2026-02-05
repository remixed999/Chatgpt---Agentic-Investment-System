from __future__ import annotations

from typing import Dict

from src.core.guards.base import NoOpGuard
from src.core.guards.g0_input_schema import G0InputSchemaGuard
from src.core.guards.g1_portfolio_context import G1PortfolioContextGuard
from src.core.guards.g7_determinism import G7DeterminismGuard


GUARD_IDS = [f"G{index}" for index in range(0, 11)]


def build_guard_registry() -> Dict[str, object]:
    registry = {
        "G0": G0InputSchemaGuard(),
        "G1": G1PortfolioContextGuard(),
        "G7": G7DeterminismGuard(),
    }
    for guard_id in GUARD_IDS:
        registry.setdefault(guard_id, NoOpGuard(guard_id))
    return registry
