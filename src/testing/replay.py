from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.core.canonicalization import (
    canonical_json_dumps,
    hash_committee_packet,
    hash_decision_payload,
    hash_portfolio_config,
    hash_portfolio_snapshot,
    hash_run_config,
    hash_run_hash,
)
from src.core.config.loader import load_json_file, load_manifest, sha256_digest
from src.core.models import (
    ConfigSnapshot,
    OrchestrationResult,
    PortfolioConfig,
    PortfolioSnapshot,
    RunConfig,
    RunOutcome,
)
from src.core.orchestration import Orchestrator


@dataclass(frozen=True)
class FixturePaths:
    portfolio_snapshot: Path
    portfolio_config: Path
    seeded: Path
    run_config: Optional[Path] = None
    config_snapshot: Optional[Path] = None
    expected: Optional[Path] = None


@dataclass(frozen=True)
class BundlePaths:
    run_config: Optional[Path] = None
    config_snapshot: Optional[Path] = None
    manifest: Optional[Path] = None


@dataclass(frozen=True)
class ReplayResult:
    hashes: Dict[str, Any]
    outcomes: Dict[str, Any]
    logs: Dict[str, Any]


def run_fixture(
    fixture_paths: FixturePaths,
    bundle_paths: BundlePaths,
    *,
    now_func: Optional[Callable[[], datetime]] = None,
) -> OrchestrationResult:
    inputs = _build_inputs(fixture_paths, bundle_paths)
    orchestrator = Orchestrator(now_func=now_func)
    return orchestrator.run(**inputs)


def compute_all_hashes(packet: OrchestrationResult, inputs: Dict[str, Any]) -> Dict[str, Any]:
    portfolio_snapshot = PortfolioSnapshot.parse_obj(inputs["portfolio_snapshot_data"])
    portfolio_config = PortfolioConfig.parse_obj(inputs["portfolio_config_data"])
    run_config = RunConfig.parse_obj(inputs["run_config_data"])
    ConfigSnapshot.parse_obj(inputs["config_snapshot_data"])

    snapshot_hash = hash_portfolio_snapshot(portfolio_snapshot)
    config_hash = hash_portfolio_config(portfolio_config)
    run_config_hash = hash_run_config(run_config)

    committee_packet = packet.portfolio_committee_packet
    holding_packet_hashes: Dict[str, str] = {}
    if packet.holding_packets:
        for holding in packet.holding_packets:
            key = holding.holding_id or "unknown"
            holding_packet_hashes[key] = canonical_json_dumps(holding)
            holding_packet_hashes[key] = sha256_digest(holding_packet_hashes[key].encode("utf-8"))

    if committee_packet is None:
        return {
            "snapshot_hash": snapshot_hash,
            "config_hash": config_hash,
            "run_config_hash": run_config_hash,
            "committee_packet_hash": None,
            "decision_hash": None,
            "run_hash": None,
            "holding_packet_hashes": holding_packet_hashes,
        }

    if packet.outcome != RunOutcome.COMPLETED:
        return {
            "snapshot_hash": snapshot_hash,
            "config_hash": config_hash,
            "run_config_hash": run_config_hash,
            "committee_packet_hash": None,
            "decision_hash": None,
            "run_hash": None,
            "holding_packet_hashes": holding_packet_hashes,
        }

    committee_packet_hash = hash_committee_packet(committee_packet)
    decision_payload = {
        "portfolio_committee_packet": committee_packet,
        "holding_packets": packet.holding_packets,
    }
    computed_decision_hash = hash_decision_payload(decision_payload)
    computed_run_hash = hash_run_hash(
        snapshot_hash=snapshot_hash,
        config_hash=config_hash,
        run_config_hash=run_config_hash,
        committee_packet_hash=committee_packet_hash,
        decision_hash=computed_decision_hash,
    )
    decision_hash = committee_packet.decision_hash or computed_decision_hash
    run_hash = committee_packet.run_hash or computed_run_hash
    if committee_packet.run_hash is None and committee_packet.decision_hash is None:
        decision_hash = None
        run_hash = None
    return {
        "snapshot_hash": snapshot_hash,
        "config_hash": config_hash,
        "run_config_hash": run_config_hash,
        "committee_packet_hash": committee_packet_hash,
        "decision_hash": decision_hash,
        "run_hash": run_hash,
        "holding_packet_hashes": holding_packet_hashes,
    }


def replay_n_times(
    fixture_id: str,
    n: int,
    *,
    fixture_paths: FixturePaths,
    bundle_paths: BundlePaths,
    now_func: Optional[Callable[[], datetime]] = None,
) -> List[ReplayResult]:
    results: List[ReplayResult] = []
    for run_index in range(n):
        inputs = _build_inputs(fixture_paths, bundle_paths)
        outcome = Orchestrator(now_func=now_func).run(**inputs)
        hashes = compute_all_hashes(outcome, inputs)
        outcomes = _collect_outcomes(outcome)
        logs = {
            "fixture_id": fixture_id,
            "run_index": run_index,
            "run_outcome": outcome.outcome.value,
            "guard_results": [guard.model_dump() for guard in outcome.guard_results],
        }
        results.append(ReplayResult(hashes=hashes, outcomes=outcomes, logs=logs))
    return results


def _build_inputs(fixture_paths: FixturePaths, bundle_paths: BundlePaths) -> Dict[str, Any]:
    run_config_path = fixture_paths.run_config or bundle_paths.run_config
    config_snapshot_path = fixture_paths.config_snapshot or bundle_paths.config_snapshot
    if run_config_path is None or config_snapshot_path is None:
        raise ValueError("RunConfig and ConfigSnapshot paths are required for replay.")

    portfolio_snapshot_data = _load_payload(fixture_paths.portfolio_snapshot)
    portfolio_config_data = _load_payload(fixture_paths.portfolio_config)
    run_config_data = _load_payload(run_config_path)
    config_snapshot_data = _load_payload(config_snapshot_path)
    seeded_data = _load_payload(fixture_paths.seeded)

    config_snapshot_data = {
        **config_snapshot_data,
        "registries": {
            **(config_snapshot_data.get("registries") or {}),
            **seeded_data,
        },
    }

    manifest_data = load_manifest(bundle_paths.manifest) if bundle_paths.manifest else None
    run_config_hash = sha256_digest(run_config_path.read_bytes())
    config_snapshot_hash = sha256_digest(config_snapshot_path.read_bytes())
    return {
        "portfolio_snapshot_data": portfolio_snapshot_data,
        "portfolio_config_data": portfolio_config_data,
        "run_config_data": run_config_data,
        "config_snapshot_data": config_snapshot_data,
        "manifest_data": manifest_data,
        "config_hashes": {
            "run_config_hash": run_config_hash,
            "config_snapshot_hash": config_snapshot_hash,
        },
    }


def _load_payload(path: Path) -> Dict[str, Any]:
    payload = load_json_file(path).data
    return payload.get("payload", payload)


def _collect_outcomes(outcome: OrchestrationResult) -> Dict[str, Any]:
    per_holding = {}
    for holding in outcome.holding_packets:
        holding_id = holding.holding_id or "unknown"
        per_holding[holding_id] = holding.holding_run_outcome.value
    portfolio_packet = outcome.portfolio_committee_packet
    portfolio_outcome = portfolio_packet.portfolio_run_outcome.value if portfolio_packet else outcome.outcome.value
    return {
        "portfolio_run_outcome": portfolio_outcome,
        "per_holding_outcomes": per_holding,
    }
