from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.schemas.models import ConfigSnapshot, HoldingInput, PortfolioConfig, PortfolioSnapshot, RunConfig


@dataclass(frozen=True)
class ValidationResult:
    portfolio_errors: List[str] = field(default_factory=list)
    holding_errors: Dict[str, List[str]] = field(default_factory=dict)
    portfolio_failed: bool = False
    portfolio_vetoed: bool = False
    portfolio_snapshot: Optional[PortfolioSnapshot] = None
    portfolio_config: Optional[PortfolioConfig] = None
    run_config: Optional[RunConfig] = None
    config_snapshot: Optional[ConfigSnapshot] = None
    valid_holdings: List[HoldingInput] = field(default_factory=list)
    portfolio_id: Optional[str] = None
