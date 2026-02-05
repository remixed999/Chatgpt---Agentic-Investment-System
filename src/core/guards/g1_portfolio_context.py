from __future__ import annotations

from typing import Optional

from src.core.guards.base import Guard, fail_result, pass_result
from src.core.models import GuardResult, PortfolioConfig, PortfolioSnapshot, RunOutcome


class G1PortfolioContextGuard(Guard):
    guard_id = "G1"

    def evaluate(
        self,
        *,
        portfolio_snapshot: PortfolioSnapshot,
        portfolio_config: Optional[PortfolioConfig],
    ) -> GuardResult:
        if portfolio_snapshot and (portfolio_config is None or not portfolio_config.base_currency):
            return fail_result(
                self.guard_id,
                RunOutcome.VETOED,
                ["missing_base_currency"],
            )
        return pass_result(self.guard_id)
