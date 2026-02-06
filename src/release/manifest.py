from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

DEFAULT_RELEASE_ID = "UNSPECIFIED_RELEASE"
DEFAULT_CREATED_AT_UTC = "1970-01-01T00:00:00Z"
REQUIRED_FILES = {
    "portfolio_snapshot.json",
    "portfolio_config.json",
    "run_config.json",
    "config_snapshot.json",
}


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle_files(bundle_dir: Path) -> List[Path]:
    return sorted(
        path
        for path in bundle_dir.iterdir()
        if path.is_file() and path.name != "release_manifest.json"
    )


def compute_manifest(bundle_dir: Path) -> Dict[str, object]:
    files = _bundle_files(bundle_dir)
    manifest_files = {path.name: _hash_file(path) for path in files}
    return {
        "release_id": DEFAULT_RELEASE_ID,
        "created_at_utc": DEFAULT_CREATED_AT_UTC,
        "files": manifest_files,
    }


def verify_manifest(bundle_dir: Path, manifest: Dict[str, object]) -> Tuple[bool, List[str]]:
    violations: List[str] = []
    release_id = manifest.get("release_id")
    created_at_utc = manifest.get("created_at_utc")
    manifest_files = manifest.get("files")

    if not isinstance(release_id, str) or not release_id:
        violations.append("Manifest release_id must be a non-empty string.")
    if not isinstance(created_at_utc, str) or not created_at_utc:
        violations.append("Manifest created_at_utc must be a non-empty string.")
    if not isinstance(manifest_files, dict):
        violations.append("Manifest files map missing or invalid.")
        return False, violations

    for required in sorted(REQUIRED_FILES):
        if required not in manifest_files:
            violations.append(f"Manifest missing required file entry: {required}.")

    bundle_files = _bundle_files(bundle_dir)
    bundle_names = {path.name for path in bundle_files}
    manifest_names = set(manifest_files.keys())

    extra = sorted(bundle_names - manifest_names)
    missing = sorted(manifest_names - bundle_names)
    if extra:
        violations.append(f"Bundle has unpinned files: {extra}.")
    if missing:
        violations.append(f"Manifest references missing bundle files: {missing}.")

    for name in sorted(bundle_names & manifest_names):
        digest = _hash_file(bundle_dir / name)
        expected = manifest_files.get(name)
        if digest != expected:
            violations.append(f"Hash mismatch for {name}: expected {expected}, got {digest}.")

    return len(violations) == 0, violations
