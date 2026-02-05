from __future__ import annotations

import hashlib
import json
from dataclasses import is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from agentic_system.schemas.contracts import ConfigSnapshot, RunConfig


# DD-11: preflight loader + hash placeholder

def _to_primitive(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_primitive(getattr(value, key)) for key in value.__dataclass_fields__}
    if isinstance(value, Mapping):
        return {key: _to_primitive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_primitive(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def compute_hash(payload: Any) -> str:
    normalized = _to_primitive(payload)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_json(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, Mapping):
        raise ValueError("Config must be a JSON object")
    return data


def load_run_config(path: Path) -> RunConfig:
    data = _load_json(path)
    return RunConfig.from_dict(data)


def load_config_snapshot(path: Path) -> ConfigSnapshot:
    data = _load_json(path)
    return ConfigSnapshot.from_dict(data)


def preflight(run_config_path: Path, config_snapshot_path: Path) -> tuple[RunConfig, ConfigSnapshot, str, str]:
    run_config = load_run_config(run_config_path)
    config_snapshot = load_config_snapshot(config_snapshot_path)
    run_config_hash = compute_hash(run_config)
    config_snapshot_hash = compute_hash(config_snapshot)
    return run_config, config_snapshot, run_config_hash, config_snapshot_hash
