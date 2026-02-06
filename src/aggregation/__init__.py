"""Aggregation engine for portfolio-level scoring and packet assembly."""

from src.aggregation.aggregator import HoldingState, build_holding_packet, build_portfolio_packet
from src.aggregation.caps import apply_lefo_caps, apply_pscc_caps
from src.aggregation.scoring import compute_base_score

__all__ = [
    "apply_lefo_caps",
    "apply_pscc_caps",
    "HoldingState",
    "build_holding_packet",
    "build_portfolio_packet",
    "compute_base_score",
]
