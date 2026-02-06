from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict

from src.core.canonicalization.canonicalize import canonical_json_dumps, canonicalize_payload
from src.core.models import (
    PortfolioConfig,
    PortfolioCommitteePacket,
    PortfolioSnapshot,
    RunConfig,
)


@dataclass(frozen=True)
class RunHashes:
    snapshot_hash: str
    config_hash: str
    run_config_hash: str
    committee_packet_hash: str
    decision_hash: str
    run_hash: str


def sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_portfolio_snapshot(snapshot: PortfolioSnapshot) -> str:
    # Hash input: canonical PortfolioSnapshot (decision-significant snapshot state).
    return _hash_payload(snapshot)


def hash_portfolio_config(config: PortfolioConfig) -> str:
    # Hash input: canonical PortfolioConfig (portfolio-level config inputs).
    return _hash_payload(config)


def hash_run_config(run_config: RunConfig) -> str:
    # Hash input: canonical RunConfig (runtime policy/config inputs).
    return _hash_payload(run_config)


def hash_committee_packet(packet: PortfolioCommitteePacket) -> str:
    # Hash input: canonical PortfolioCommitteePacket (ordered committee output packet).
    return _hash_payload(packet)


def hash_decision_payload(payload: Any) -> str:
    # Hash input: canonical decision payload (portfolio committee packet + holding packets).
    return _hash_payload(payload)


def compute_run_hashes(
    *,
    portfolio_snapshot: PortfolioSnapshot,
    portfolio_config: PortfolioConfig,
    run_config: RunConfig,
    committee_packet: PortfolioCommitteePacket,
    decision_payload: Any,
) -> RunHashes:
    # Hash inputs are the canonicalized decision-significant inputs and outputs defined by DD-07.
    snapshot_hash = hash_portfolio_snapshot(portfolio_snapshot)
    config_hash = hash_portfolio_config(portfolio_config)
    run_config_hash = hash_run_config(run_config)
    committee_packet_hash = hash_committee_packet(committee_packet)
    decision_hash = hash_decision_payload(decision_payload)
    run_hash = hash_run_hash(
        snapshot_hash=snapshot_hash,
        config_hash=config_hash,
        run_config_hash=run_config_hash,
        committee_packet_hash=committee_packet_hash,
        decision_hash=decision_hash,
    )
    return RunHashes(
        snapshot_hash=snapshot_hash,
        config_hash=config_hash,
        run_config_hash=run_config_hash,
        committee_packet_hash=committee_packet_hash,
        decision_hash=decision_hash,
        run_hash=run_hash,
    )


def hash_run_hash(
    *,
    snapshot_hash: str,
    config_hash: str,
    run_config_hash: str,
    committee_packet_hash: str,
    decision_hash: str,
) -> str:
    composite = {
        "snapshot_hash": snapshot_hash,
        "config_hash": config_hash,
        "run_config_hash": run_config_hash,
        "committee_packet_hash": committee_packet_hash,
        "decision_hash": decision_hash,
    }
    return sha256_text(canonical_json_dumps(composite))


def replay_hashes_match(payload_a: Any, payload_b: Any) -> bool:
    return sha256_text(canonical_json_dumps(canonicalize_payload(payload_a))) == sha256_text(
        canonical_json_dumps(canonicalize_payload(payload_b))
    )


def replay_hashes_ignore_timestamps(payload_a: Any, payload_b: Any) -> bool:
    return replay_hashes_match(payload_a, payload_b)


def _hash_payload(payload: Any) -> str:
    return sha256_text(canonical_json_dumps(payload))
