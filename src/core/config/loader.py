from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LoadedJson:
    data: Dict[str, Any]
    raw_bytes: bytes


def load_json_file(path: Path) -> LoadedJson:
    raw_bytes = path.read_bytes()
    data = json.loads(raw_bytes.decode("utf-8"))
    return LoadedJson(data=data, raw_bytes=raw_bytes)


def sha256_digest(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def load_manifest(path: Optional[Path]) -> Optional[Dict[str, str]]:
    if path is None:
        return None
    return load_json_file(path).data
