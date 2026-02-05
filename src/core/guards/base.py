from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.models import GuardResult, RunOutcome


class Guard(ABC):
    guard_id: str

    @abstractmethod
    def evaluate(self, **kwargs) -> GuardResult:
        raise NotImplementedError


class NoOpGuard(Guard):
    def __init__(self, guard_id: str) -> None:
        self.guard_id = guard_id

    def evaluate(self, **kwargs) -> GuardResult:
        return GuardResult(guard_id=self.guard_id, status="skipped", outcome=None, reasons=[])


def fail_result(guard_id: str, outcome: RunOutcome, reasons: Optional[List[str]] = None) -> GuardResult:
    return GuardResult(
        guard_id=guard_id,
        status="failed" if outcome == RunOutcome.FAILED else "vetoed",
        outcome=outcome,
        reasons=reasons or [],
    )


def pass_result(guard_id: str) -> GuardResult:
    return GuardResult(guard_id=guard_id, status="passed", outcome=None, reasons=[])
