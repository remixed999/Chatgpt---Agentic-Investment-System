from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping


# DD-08: guard interface only
class Guard(ABC):
    @abstractmethod
    def evaluate(self, context: Mapping[str, Any]) -> None:
        raise NotImplementedError
