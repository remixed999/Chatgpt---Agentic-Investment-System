from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from src.core.models import GuardResult, RunOutcome


class GuardScope(str, Enum):
    PORTFOLIO = "portfolio"
    HOLDING = "holding"


class GuardSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class GuardViolation:
    scope: GuardScope
    outcome: RunOutcome
    reason: str
    holding_id: Optional[str] = None
    holding_index: Optional[int] = None


@dataclass
class GuardEvaluation:
    result: GuardResult
    violations: List[GuardViolation] = field(default_factory=list)


class Guard(ABC):
    guard_id: str

    @abstractmethod
    def evaluate(self, **kwargs) -> GuardEvaluation:
        raise NotImplementedError


class NoOpGuard(Guard):
    def __init__(self, guard_id: str) -> None:
        self.guard_id = guard_id

    def evaluate(self, **kwargs) -> GuardEvaluation:
        return GuardEvaluation(
            result=GuardResult(guard_id=self.guard_id, status="skipped", outcome=None, reasons=[]),
        )


def fail_result(guard_id: str, outcome: RunOutcome, reasons: Optional[List[str]] = None) -> GuardResult:
    status = "failed"
    if outcome == RunOutcome.VETOED:
        status = "vetoed"
    elif outcome == RunOutcome.SHORT_CIRCUITED:
        status = "short_circuited"
    return GuardResult(
        guard_id=guard_id,
        status=status,
        outcome=outcome,
        reasons=reasons or [],
    )


def pass_result(guard_id: str) -> GuardResult:
    return GuardResult(guard_id=guard_id, status="passed", outcome=None, reasons=[])
