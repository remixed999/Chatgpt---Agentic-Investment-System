from __future__ import annotations

from typing import Dict, Optional

from src.core.guards.base import Guard, fail_result, pass_result
from src.core.models import GuardResult, RunOutcome


class G0InputSchemaGuard(Guard):
    guard_id = "G0"

    def evaluate(
        self,
        *,
        manifest: Optional[Dict[str, str]],
        config_hashes: Dict[str, str],
    ) -> GuardResult:
        if manifest is None:
            return pass_result(self.guard_id)

        expected_run_config = manifest.get("run_config_hash")
        expected_config_snapshot = manifest.get("config_snapshot_hash")

        missing_keys = [
            key
            for key in ("run_config_hash", "config_snapshot_hash")
            if key not in manifest
        ]
        if missing_keys:
            reasons = [f"manifest_missing_{key}" for key in missing_keys]
            return fail_result(self.guard_id, RunOutcome.FAILED, reasons)

        mismatches = []
        if expected_run_config != config_hashes.get("run_config_hash"):
            mismatches.append("run_config_hash_mismatch")
        if expected_config_snapshot != config_hashes.get("config_snapshot_hash"):
            mismatches.append("config_snapshot_hash_mismatch")

        if mismatches:
            return fail_result(self.guard_id, RunOutcome.FAILED, mismatches)

        return pass_result(self.guard_id)
