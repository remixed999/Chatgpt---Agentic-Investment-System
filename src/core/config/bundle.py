from __future__ import annotations

from dataclasses import dataclass

from src.schemas.models import ConfigSnapshot, PortfolioConfig, PortfolioSnapshot, RunConfig


@dataclass(frozen=True)
class ConfigBundle:
    portfolio_snapshot: PortfolioSnapshot
    portfolio_config: PortfolioConfig
    run_config: RunConfig
    config_snapshot: ConfigSnapshot
