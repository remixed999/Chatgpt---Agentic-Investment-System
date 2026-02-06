from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.models import CapOverride, Scorecard


def apply_lefo_caps(scorecard: Scorecard, lefo_output: Optional[Dict[str, Any]]) -> Scorecard:
    if not lefo_output:
        return scorecard
    cap_value = _extract_cap_value(lefo_output)
    if cap_value is None:
        return scorecard

    if scorecard.base_score is None or scorecard.base_score > cap_value:
        scorecard.base_score = cap_value
        scorecard.applied_caps.append(
            CapOverride(
                source="LEFO",
                cap_value=cap_value,
                reason="lefo_liquidity_cap",
            )
        )
    return scorecard


def apply_pscc_caps(
    scorecard: Scorecard,
    pscc_output: Optional[Dict[str, Any]],
    holding_id: Optional[str],
) -> Scorecard:
    if not pscc_output or not holding_id:
        return scorecard
    cap_value = _extract_pscc_cap(pscc_output, holding_id)
    if cap_value is None:
        return scorecard

    if scorecard.base_score is None or scorecard.base_score > cap_value:
        scorecard.base_score = cap_value
        scorecard.applied_caps.append(
            CapOverride(
                source="PSCC",
                cap_value=cap_value,
                reason="pscc_position_cap",
            )
        )
    return scorecard


def _extract_cap_value(lefo_output: Dict[str, Any]) -> Optional[float]:
    cap = lefo_output.get("score_cap")
    if cap is None:
        cap = lefo_output.get("max_score")
    if cap is None:
        return None
    return float(cap)


def _extract_pscc_cap(pscc_output: Dict[str, Any], holding_id: str) -> Optional[float]:
    caps = pscc_output.get("position_caps_applied")
    if isinstance(caps, dict):
        cap_entry = caps.get(holding_id)
        return _cap_value_from_entry(cap_entry)
    if isinstance(caps, list):
        for entry in caps:
            if isinstance(entry, dict) and entry.get("holding_id") == holding_id:
                return _cap_value_from_entry(entry)
    return None


def _cap_value_from_entry(entry: Any) -> Optional[float]:
    if entry is None:
        return None
    if isinstance(entry, (int, float)):
        return float(entry)
    if isinstance(entry, dict):
        for key in ("score_cap", "max_score", "cap_score"):
            if key in entry:
                return float(entry[key])
    return None
