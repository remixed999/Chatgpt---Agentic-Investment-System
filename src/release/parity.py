from __future__ import annotations

import re
import time
from pathlib import Path
from typing import List

from src.core.canonicalization import canonical_json_dumps
from src.core.utils.determinism import stable_json_dumps

PARITY_SCAN_PATHS = [
    Path("src/cli/release_phase0.py"),
    Path("src/release/manifest.py"),
    Path("src/release/parity.py"),
]

FORBIDDEN_RUNTIME_PATTERNS = [
    (re.compile(r"datetime" + r"\.now"), "datetime now usage is forbidden in Phase 0/1 tooling."),
    (re.compile(r"time" + r"\.time\("), "time time usage is forbidden in Phase 0/1 tooling."),
    (re.compile(r"uuid" + r"4\("), "uuid 4 usage is forbidden in Phase 0/1 tooling."),
]


def _check_timezone_utc(violations: List[str]) -> None:
    if time.timezone != 0 or time.altzone != 0 or time.daylight:
        violations.append("Timezone is not UTC-only; set TZ=UTC for Phase 0 readiness.")
    tzname = time.tzname
    if tzname and all(name not in {"UTC", "GMT"} for name in tzname):
        violations.append(f"Timezone names not UTC/GMT: {tzname}.")


def _check_serialization(violations: List[str]) -> None:
    payload = {"a": 1, "b": [3, 2, 1], "c": {"d": 1.23}}
    first = stable_json_dumps(payload)
    second = stable_json_dumps(payload)
    if first != second:
        violations.append("stable_json_dumps is not deterministic within process.")

    float_payload = {"small": 1e-6, "trail": 1.2300, "whole": 2.0}
    encoded = canonical_json_dumps(float_payload)
    if re.search(r"[0-9]+e[+-]?[0-9]+", encoded, flags=re.IGNORECASE):
        violations.append("Canonical float formatting uses exponent notation; disallowed by DD-07.")
    if "1.2300" in encoded or "2.0" in encoded:
        violations.append("Canonical float formatting does not trim trailing zeros.")


def _check_forbidden_runtime_patterns(violations: List[str]) -> None:
    for path in PARITY_SCAN_PATHS:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for pattern, message in FORBIDDEN_RUNTIME_PATTERNS:
            if pattern.search(content):
                violations.append(f"{message} ({path})")


def run_parity_checks() -> List[str]:
    violations: List[str] = []
    _check_timezone_utc(violations)
    _check_serialization(violations)
    _check_forbidden_runtime_patterns(violations)
    return violations
