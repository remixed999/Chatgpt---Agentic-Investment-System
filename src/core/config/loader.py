from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.config.bundle import ConfigBundle
from src.schemas.models import ConfigSnapshot, PortfolioConfig, PortfolioSnapshot, RunConfig


@dataclass(frozen=True)
class LoadedJson:
    data: Dict[str, Any]
    raw_bytes: bytes


def load_json_file(path: Path) -> LoadedJson:
    raw_bytes = path.read_bytes()
    data = json.loads(raw_bytes.decode("utf-8"))
    return LoadedJson(data=data, raw_bytes=raw_bytes)


def load_json(path: Path) -> Dict[str, Any]:
    data = load_json_file(path).data
    if isinstance(data, dict) and "payload" in data:
        return data["payload"]
    return data


def sha256_digest(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def load_manifest(path: Optional[Path]) -> Optional[Dict[str, str]]:
    if path is None:
        return None
    return load_json_file(path).data


def load_bundle(bundle_dir: Path) -> ConfigBundle:
    snapshot_data = load_json(bundle_dir / "portfolio_snapshot.json")
    portfolio_config_data = load_json(bundle_dir / "portfolio_config.json")
    run_config_data = load_json(bundle_dir / "run_config.json")
    config_snapshot_data = load_json(bundle_dir / "config_snapshot.json")

    return ConfigBundle(
        portfolio_snapshot=PortfolioSnapshot.model_validate(snapshot_data),
        portfolio_config=PortfolioConfig.model_validate(portfolio_config_data),
        run_config=RunConfig.model_validate(run_config_data),
        config_snapshot=ConfigSnapshot.model_validate(config_snapshot_data),
    )
