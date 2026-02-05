from __future__ import annotations

from typing import Optional

from src.core.guards.base import Guard, fail_result, pass_result
from src.core.models import GuardResult, RunOutcome


class G7DeterminismGuard(Guard):
    guard_id = "G7"

    def evaluate(
        self,
        *,
        snapshot_hash: Optional[str],
        config_hash: Optional[str],
        run_config_hash: Optional[str],
        committee_packet_hash: Optional[str],
        decision_hash: Optional[str],
        run_hash: Optional[str],
    ) -> GuardResult:
        required = [
            snapshot_hash,
            config_hash,
            run_config_hash,
            committee_packet_hash,
            decision_hash,
            run_hash,
        ]
        if any(not value for value in required):
            return fail_result(self.guard_id, RunOutcome.FAILED, ["determinism_hash_missing"])
        return pass_result(self.guard_id)
