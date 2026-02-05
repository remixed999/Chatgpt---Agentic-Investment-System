from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pydantic import ValidationError

from src.agents.base import BaseAgent
from src.agents.registry import AgentRegistry, get_default_registry
from src.core.models import AgentResult, ConfigSnapshot, HoldingInput, PortfolioConfig, PortfolioSnapshot, RunConfig


@dataclass(frozen=True)
class PortfolioAgentContext:
    portfolio_snapshot: PortfolioSnapshot
    portfolio_config: PortfolioConfig
    run_config: RunConfig
    config_snapshot: ConfigSnapshot
    ordered_holdings: List[HoldingInput]
    agent_results: List[AgentResult]


@dataclass(frozen=True)
class HoldingAgentContext:
    holding: HoldingInput
    portfolio_snapshot: PortfolioSnapshot
    portfolio_config: PortfolioConfig
    run_config: RunConfig
    config_snapshot: ConfigSnapshot
    ordered_holdings: List[HoldingInput]
    agent_results: List[AgentResult]


def run_portfolio_agents(
    phase: str,
    context: PortfolioAgentContext,
    *,
    registry: Optional[AgentRegistry] = None,
) -> List[AgentResult]:
    registry = registry or get_default_registry()
    return _run_agents(registry.agents_for_phase(phase=phase, scope="portfolio"), context)


def run_holding_agents(
    phase: str,
    context: HoldingAgentContext,
    *,
    registry: Optional[AgentRegistry] = None,
) -> List[AgentResult]:
    registry = registry or get_default_registry()
    return _run_agents(registry.agents_for_phase(phase=phase, scope="holding"), context)


def _run_agents(agents: List[BaseAgent], context: object) -> List[AgentResult]:
    results: List[AgentResult] = []
    for agent in agents:
        try:
            result = agent.execute(context)
            if isinstance(result, AgentResult):
                results.append(result)
            else:
                results.append(AgentResult.parse_obj(result))
        except ValidationError as exc:
            results.append(_failed_result(agent, context, f"validation_error:{exc.__class__.__name__}"))
        except Exception as exc:  # noqa: BLE001 - deterministic failure handling
            results.append(_failed_result(agent, context, f"agent_exception:{exc.__class__.__name__}"))
    return results


def _failed_result(agent: BaseAgent, context: object, reason: str) -> AgentResult:
    holding_id = None
    if agent.scope == "holding":
        holding = getattr(context, "holding", None)
        if holding and holding.identity:
            holding_id = holding.identity.holding_id
    return AgentResult(
        agent_name=agent.agent_name,
        scope=agent.scope,
        status="failed",
        confidence=0.0,
        key_findings={"conformance_error": True, "error": reason},
        metrics=[],
        suggested_penalties=[],
        veto_flags=[],
        holding_id=holding_id,
    )
