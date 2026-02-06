from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from src.core.models import AgentResult, HoldingInput


def compute_base_score(
    holding_context: HoldingInput,
    rubric: Optional[Dict[str, Any]],
    agent_results: Iterable[AgentResult],
) -> Optional[float]:
    if not rubric:
        return None
    dimensions = rubric.get("dimensions", [])
    if not dimensions:
        return None

    total_weight = 0.0
    total_score = 0.0
    for dimension in dimensions:
        metric_key = dimension.get("metric_key")
        weight = float(dimension.get("weight", 0.0))
        if weight <= 0.0:
            continue
        total_weight += weight
        if not metric_key:
            return None
        metric = holding_context.metrics.get(metric_key)
        if metric is None or metric.value is None or metric.not_applicable:
            if dimension.get("missing_policy", "require") == "omit":
                total_weight -= weight
                continue
            return None
        normalized = _normalize_metric_value(metric.value, dimension)
        if normalized is None:
            return None
        total_score += normalized * weight

    if total_weight <= 0.0:
        return None
    if abs(total_weight - 100.0) > 1e-6:
        return (total_score / total_weight) * 100.0
    return total_score


def _normalize_metric_value(value: float, dimension: Dict[str, Any]) -> Optional[float]:
    scale_min = dimension.get("scale_min")
    scale_max = dimension.get("scale_max")
    higher_is_better = dimension.get("higher_is_better", True)

    if scale_min is None or scale_max is None:
        normalized = float(value)
    else:
        span = float(scale_max) - float(scale_min)
        if span == 0:
            return None
        normalized = (float(value) - float(scale_min)) / span

    if not higher_is_better:
        normalized = 1.0 - normalized
    return max(0.0, min(1.0, normalized))
