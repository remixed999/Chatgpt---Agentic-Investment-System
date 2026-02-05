from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.agents.base import BaseAgent
from src.agents.devils_advocate import DevilsAdvocateAgent
from src.agents.dio import DIOAgent
from src.agents.fundamentals import FundamentalsAgent
from src.agents.grra import GRRAAgent
from src.agents.lefo import LEFOAgent
from src.agents.pscc import PSCCAgent
from src.agents.risk_officer import RiskOfficerAgent
from src.agents.technical import TechnicalAgent


DEFAULT_REGISTRY_PATH = Path("config/agent_registry.json")


@dataclass(frozen=True)
class AgentSpec:
    name: str
    version: str
    enabled: bool


DEFAULT_AGENT_SPECS: Dict[str, AgentSpec] = {
    "DIO": AgentSpec(name="DIO", version="0.1", enabled=True),
    "GRRA": AgentSpec(name="GRRA", version="0.1", enabled=True),
    "LEFO": AgentSpec(name="LEFO", version="0.1", enabled=True),
    "PSCC": AgentSpec(name="PSCC", version="0.1", enabled=True),
    "RiskOfficer": AgentSpec(name="RiskOfficer", version="0.1", enabled=True),
    "Fundamentals": AgentSpec(name="Fundamentals", version="0.1", enabled=True),
    "Technical": AgentSpec(name="Technical", version="0.1", enabled=True),
    "DevilsAdvocate": AgentSpec(name="DevilsAdvocate", version="0.1", enabled=True),
}

DEFAULT_PHASES: Dict[str, List[str]] = {
    "DIO": ["DIO"],
    "GRRA": ["GRRA"],
    "LEFO_PSCC": ["LEFO", "PSCC"],
    "RISK_OFFICER": ["RiskOfficer"],
    "ANALYTICAL": ["Fundamentals", "Technical", "DevilsAdvocate"],
}

DEFAULT_AGENT_CLASSES: Dict[str, type[BaseAgent]] = {
    "DIO": DIOAgent,
    "GRRA": GRRAAgent,
    "LEFO": LEFOAgent,
    "PSCC": PSCCAgent,
    "RiskOfficer": RiskOfficerAgent,
    "Fundamentals": FundamentalsAgent,
    "Technical": TechnicalAgent,
    "DevilsAdvocate": DevilsAdvocateAgent,
}


class AgentRegistry:
    def __init__(
        self,
        *,
        config_data: Optional[Dict[str, Any]] = None,
        agent_classes: Optional[Dict[str, type[BaseAgent]]] = None,
    ) -> None:
        self._agent_classes = agent_classes or DEFAULT_AGENT_CLASSES
        if config_data is None:
            config_data = self._load_default_config()
        self._agent_specs = self._load_agent_specs(config_data)
        self._phases = self._load_phase_order(config_data)

    def agents_for_phase(self, *, phase: str, scope: str) -> List[BaseAgent]:
        agents: List[BaseAgent] = []
        for name in self._phases.get(phase, []):
            spec = self._agent_specs.get(name)
            if spec is None or not spec.enabled:
                continue
            agent_class = self._agent_classes.get(name)
            if agent_class is None:
                continue
            if scope not in agent_class.supported_scopes():
                continue
            agents.append(agent_class(agent_name=name, agent_version=spec.version, scope=scope))
        return agents

    @staticmethod
    def _load_default_config() -> Dict[str, Any]:
        if DEFAULT_REGISTRY_PATH.exists():
            return json.loads(DEFAULT_REGISTRY_PATH.read_text(encoding="utf-8"))
        return {"agents": {}, "phases": {}}

    @staticmethod
    def _load_agent_specs(config_data: Dict[str, Any]) -> Dict[str, AgentSpec]:
        specs: Dict[str, AgentSpec] = {}
        raw_specs = config_data.get("agents", {})
        for name, payload in raw_specs.items():
            specs[name] = AgentSpec(
                name=name,
                version=str(payload.get("version", DEFAULT_AGENT_SPECS.get(name, AgentSpec(name, "0.1", True)).version)),
                enabled=bool(payload.get("enabled", DEFAULT_AGENT_SPECS.get(name, AgentSpec(name, "0.1", True)).enabled)),
            )
        for name, spec in DEFAULT_AGENT_SPECS.items():
            specs.setdefault(name, spec)
        return specs

    @staticmethod
    def _load_phase_order(config_data: Dict[str, Any]) -> Dict[str, List[str]]:
        phases = {phase: list(order) for phase, order in config_data.get("phases", {}).items()}
        for phase, order in DEFAULT_PHASES.items():
            phases.setdefault(phase, order)
        return phases


def get_default_registry() -> AgentRegistry:
    return AgentRegistry()
