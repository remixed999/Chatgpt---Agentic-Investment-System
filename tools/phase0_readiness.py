from __future__ import annotations

import argparse
import json
import locale
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from src.core.canonicalization import canonical_json_dumps
from src.core.canonicalization.hashing import sha256_text
from src.core.config.loader import load_json_file
from src.core.models import ConfigSnapshot, PortfolioCommitteePacket, PortfolioSnapshot, RunConfig


UTC = timezone.utc
ISO_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
RELATIVE_TIME_MARKERS = ("now()", "today", "yesterday")
REQUIRED_FIXTURE_METADATA = ("fixture_id", "version", "description", "created_at_utc")
REQUIRED_FIXTURE_DIRS = ("config", "portfolio", "seeded", "expected")


@dataclass(frozen=True)
class Phase0Paths:
    config_dir: Path
    fixtures_dir: Path
    output_dir: Path
    repo_root: Path


@dataclass(frozen=True)
class Phase0Result:
    manifest_path: Optional[Path]
    attestation_path: Path
    errors: List[str]


class Phase0Error(Exception):
    pass


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 0 pre-deployment readiness gate")
    parser.add_argument("--release", required=True, help="Release identifier")
    parser.add_argument("--config-dir", required=True, help="Directory with config artifacts")
    parser.add_argument("--fixtures-dir", required=True, help="Directory with fixtures")
    parser.add_argument("--out", required=True, help="Output directory for release manifests")
    return parser.parse_args(argv)


def _now_iso_utc(now_func: Callable[[], datetime]) -> str:
    return now_func().astimezone(UTC).isoformat().replace("+00:00", "Z")


def _resolve_repo_root(start: Path) -> Path:
    return start.resolve()


def _ensure_locale_invariant(errors: List[str]) -> None:
    try:
        locale.setlocale(locale.LC_NUMERIC, "C")
    except locale.Error as exc:
        errors.append(f"Locale invariant check failed: {exc}")


def _ensure_timezone_utc(errors: List[str]) -> None:
    offset = datetime.utcnow().replace(tzinfo=UTC).astimezone().utcoffset()
    if offset is None or offset.total_seconds() != 0:
        errors.append("Timezone is not UTC; set TZ=UTC for Phase 0 readiness.")


def _ensure_serialization_invariance(errors: List[str]) -> None:
    payload = {"a": 1, "b": [3, 2, 1], "c": {"d": 1.2300}}
    first = canonical_json_dumps(payload)
    second = canonical_json_dumps(payload)
    if first != second:
        errors.append("Canonical JSON serializer is not deterministic within process.")

    float_payload = {"small": 1e-6, "trail": 1.2300, "whole": 2.0}
    encoded = canonical_json_dumps(float_payload)
    if re.search(r"[0-9]+e[+-]?[0-9]+", encoded, flags=re.IGNORECASE):
        errors.append("Canonical float formatting uses exponent notation; disallowed by DD-07.")
    if "1.2300" in encoded or "2.0" in encoded:
        errors.append("Canonical float formatting does not trim trailing zeros.")


def _walk_values(value: Any) -> Iterable[Tuple[Tuple[str, ...], Any]]:
    stack: List[Tuple[Tuple[str, ...], Any]] = [((), value)]
    while stack:
        path, current = stack.pop()
        yield path, current
        if isinstance(current, dict):
            for key, item in current.items():
                stack.append((path + (str(key),), item))
        elif isinstance(current, list):
            for index, item in enumerate(current):
                stack.append((path + (str(index),), item))


def _check_fixture_metadata(payload: Dict[str, Any], path: Path, errors: List[str]) -> None:
    for key in REQUIRED_FIXTURE_METADATA:
        if key not in payload:
            errors.append(f"Fixture {path} missing required metadata field '{key}'.")
    created_at = payload.get("created_at_utc")
    if isinstance(created_at, str) and not created_at.endswith("Z"):
        errors.append(f"Fixture {path} created_at_utc must end with 'Z'.")


def _check_fixture_timestamps(payload: Dict[str, Any], path: Path, errors: List[str]) -> None:
    for field_path, value in _walk_values(payload):
        if isinstance(value, str):
            lowered = value.lower()
            if any(marker in lowered for marker in RELATIVE_TIME_MARKERS):
                errors.append(f"Fixture {path} contains non-deterministic timestamp at {'.'.join(field_path)}.")
            if ISO_TIMESTAMP_RE.search(value) and not value.endswith("Z"):
                errors.append(
                    f"Fixture {path} timestamp at {'.'.join(field_path)} must be fixed UTC ending with 'Z'."
                )


def _check_seeded_source_refs(payload: Dict[str, Any], path: Path, errors: List[str]) -> None:
    for field_path, value in _walk_values(payload):
        if isinstance(value, dict) and "value" in value:
            numeric = value.get("value")
            if isinstance(numeric, (int, float)):
                source_ref = value.get("source_ref") or value.get("sourceRef")
                if not isinstance(source_ref, dict):
                    errors.append(
                        f"Seeded fixture {path} numeric value at {'.'.join(field_path + ('value',))} missing SourceRef."
                    )
                else:
                    missing = [
                        key
                        for key in ("origin", "as_of_date", "retrieval_timestamp")
                        if key not in source_ref
                    ]
                    if missing:
                        errors.append(
                            f"Seeded fixture {path} SourceRef at {'.'.join(field_path)} missing {missing}."
                        )


def _parse_run_config(payload: Dict[str, Any], path: Path, errors: List[str]) -> Optional[RunConfig]:
    try:
        return RunConfig.parse_obj(payload)
    except Exception as exc:
        errors.append(f"RunConfig schema validation failed for {path}: {exc}")
        return None


def _parse_config_snapshot(payload: Dict[str, Any], path: Path, errors: List[str]) -> Optional[ConfigSnapshot]:
    try:
        return ConfigSnapshot.parse_obj(payload)
    except Exception as exc:
        errors.append(f"ConfigSnapshot schema validation failed for {path}: {exc}")
        return None


def _parse_portfolio_snapshot(payload: Dict[str, Any], path: Path, errors: List[str]) -> Optional[PortfolioSnapshot]:
    try:
        return PortfolioSnapshot.parse_obj(payload)
    except Exception as exc:
        errors.append(f"PortfolioSnapshot schema validation failed for {path}: {exc}")
        return None


def _parse_expected_packet(payload: Dict[str, Any], path: Path, errors: List[str]) -> Optional[PortfolioCommitteePacket]:
    try:
        return PortfolioCommitteePacket.parse_obj(payload)
    except Exception as exc:
        errors.append(f"Expected packet schema validation failed for {path}: {exc}")
        return None


def _extract_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    return data.get("payload", data)


def _find_json_files(directory: Path) -> List[Path]:
    return sorted(path for path in directory.rglob("*.json") if path.is_file())


def _find_config_snapshot_file(config_dir: Path, errors: List[str]) -> Optional[Path]:
    candidates = [
        path
        for path in _find_json_files(config_dir)
        if "config_snapshot" in path.name.lower() or "configsnapshot" in path.name.lower()
    ]
    if not candidates:
        errors.append(f"No ConfigSnapshot JSON found in {config_dir}.")
        return None
    if len(candidates) > 1:
        errors.append(f"Multiple ConfigSnapshot files found in {config_dir}: {candidates}.")
        return None
    return candidates[0]


def _find_run_config_files(config_dir: Path, errors: List[str]) -> List[Path]:
    candidates = [
        path
        for path in _find_json_files(config_dir)
        if "runconfig" in path.name.lower() or "run_config" in path.name.lower()
    ]
    if not candidates:
        errors.append(f"No RunConfig JSON files found in {config_dir}.")
    return sorted(candidates)


def _ensure_versions_pinned(payload: Any, path: Path, errors: List[str]) -> None:
    for field_path, value in _walk_values(payload):
        if not field_path:
            continue
        last = field_path[-1].lower()
        if "version" in last and isinstance(value, str):
            if value.strip().lower() == "latest":
                errors.append(f"Unpinned version 'latest' found at {path}:{'.'.join(field_path)}")


def _hash_payload(payload: Any) -> str:
    return sha256_text(canonical_json_dumps(payload))


def _relative_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _collect_registry_bundle(
    config_snapshot_data: Dict[str, Any],
    repo_root: Path,
    errors: List[str],
) -> Tuple[Dict[str, Any], List[Path]]:
    registries = config_snapshot_data.get("registries") or {}
    bundle: Dict[str, Any] = {}
    registry_paths: List[Path] = []
    for name, entry in registries.items():
        if isinstance(entry, dict) and "path" in entry:
            registry_path = Path(entry["path"])
            if not registry_path.is_absolute():
                registry_path = repo_root / registry_path
            if not registry_path.exists():
                errors.append(f"Registry file not found for '{name}': {registry_path}")
                continue
            raw_bytes = registry_path.read_bytes()
            expected_hash = entry.get("hash")
            actual_hash = sha256_text(raw_bytes.decode("utf-8"))
            if expected_hash and expected_hash != actual_hash:
                errors.append(
                    f"Registry hash mismatch for '{name}': expected {expected_hash}, got {actual_hash}"
                )
            registry_paths.append(registry_path)
            bundle[name] = json.loads(raw_bytes.decode("utf-8"))
        else:
            bundle[name] = entry
    return bundle, registry_paths


def _validate_fixture_pack(fixtures_dir: Path, errors: List[str]) -> List[Path]:
    fixture_files: List[Path] = []
    for subdir in REQUIRED_FIXTURE_DIRS:
        subdir_path = fixtures_dir / subdir
        if not subdir_path.exists():
            errors.append(f"Fixture directory missing: {subdir_path}")
            continue
        files = _find_json_files(subdir_path)
        if not files:
            errors.append(f"Fixture directory {subdir_path} contains no JSON fixtures.")
            continue
        fixture_files.extend(files)

    for fixture_path in fixture_files:
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        _check_fixture_metadata(data, fixture_path, errors)
        _check_fixture_timestamps(data, fixture_path, errors)
        payload = _extract_payload(data)
        if fixture_path.parts[-2] == "config":
            name = fixture_path.name.lower()
            if "runconfig" in name or "run_config" in name:
                _parse_run_config(payload, fixture_path, errors)
            elif "configsnapshot" in name or "config_snapshot" in name:
                _parse_config_snapshot(payload, fixture_path, errors)
        elif fixture_path.parts[-2] == "portfolio":
            _parse_portfolio_snapshot(payload, fixture_path, errors)
        elif fixture_path.parts[-2] == "expected":
            _parse_expected_packet(payload, fixture_path, errors)
        elif fixture_path.parts[-2] == "seeded":
            _check_seeded_source_refs(payload, fixture_path, errors)

    return fixture_files


def _git_commit_hash(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _format_attestation(
    release_id: str,
    created_at: str,
    errors: List[str],
    run_config_hashes: Dict[str, str],
    config_snapshot_hash: Optional[str],
    registry_bundle_hash: Optional[str],
) -> str:
    status = "PASSED" if not errors else "FAILED"
    lines = [
        f"# Phase 0 Readiness Attestation ({release_id})",
        "",
        f"Status: **{status}**",
        f"Generated at (UTC): {created_at}",
        "",
        "## Checks",
        "- Config bundle completeness (RunConfig, ConfigSnapshot, registries)",
        "- Schema/contract conformance (DD-01/DD-02/DD-03)",
        "- Hash computation + drift detection (DD-07)",
        "- Environment parity (UTC, locale invariance, serialization invariance)",
        "- Fixture compliance (DD-09)",
    ]
    if run_config_hashes:
        lines.append("\n## RunConfig hashes")
        for name, value in sorted(run_config_hashes.items()):
            lines.append(f"- {name}: `{value}`")
    if config_snapshot_hash:
        lines.append(f"\nConfigSnapshot hash: `{config_snapshot_hash}`")
    if registry_bundle_hash:
        lines.append(f"\nRegistry bundle hash: `{registry_bundle_hash}`")
    if errors:
        lines.append("\n## Errors")
        lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines) + "\n"


def run_phase0_readiness(
    argv: Sequence[str],
    *,
    now_func: Callable[[], datetime] = lambda: datetime.utcnow().replace(tzinfo=UTC),
) -> Phase0Result:
    args = _parse_args(argv)
    repo_root = _resolve_repo_root(Path.cwd())
    paths = Phase0Paths(
        config_dir=Path(args.config_dir),
        fixtures_dir=Path(args.fixtures_dir),
        output_dir=Path(args.out),
        repo_root=repo_root,
    )
    errors: List[str] = []

    _ensure_timezone_utc(errors)
    _ensure_locale_invariant(errors)
    _ensure_serialization_invariance(errors)

    config_snapshot_path = _find_config_snapshot_file(paths.config_dir, errors)
    run_config_paths = _find_run_config_files(paths.config_dir, errors)

    run_config_hashes: Dict[str, str] = {}
    config_snapshot_hash: Optional[str] = None
    registry_bundle_hash: Optional[str] = None
    registry_paths: List[Path] = []

    if config_snapshot_path:
        config_snapshot_data = load_json_file(config_snapshot_path).data
        config_snapshot_payload = _extract_payload(config_snapshot_data)
        _parse_config_snapshot(config_snapshot_payload, config_snapshot_path, errors)
        _ensure_versions_pinned(config_snapshot_payload, config_snapshot_path, errors)

        registries = config_snapshot_payload.get("registries") or {}
        for required_key in ("hard_stop_field_registry", "penalty_critical_field_registry"):
            if required_key not in registries:
                errors.append(f"ConfigSnapshot missing required registry '{required_key}'.")

        bundle, registry_paths = _collect_registry_bundle(config_snapshot_payload, paths.repo_root, errors)
        if bundle:
            registry_bundle_hash = _hash_payload(bundle)
        config_snapshot_hash = _hash_payload(config_snapshot_payload)

    for run_config_path in run_config_paths:
        run_config_data = load_json_file(run_config_path).data
        run_config_payload = _extract_payload(run_config_data)
        run_config = _parse_run_config(run_config_payload, run_config_path, errors)
        _ensure_versions_pinned(run_config_payload, run_config_path, errors)
        if run_config is None:
            continue
        run_config_hashes[run_config_path.stem] = _hash_payload(run_config_payload)

    fixture_files = _validate_fixture_pack(paths.fixtures_dir, errors)

    output_release_dir = paths.output_dir / args.release
    output_release_dir.mkdir(parents=True, exist_ok=True)
    created_at = _now_iso_utc(now_func)

    manifest_path: Optional[Path] = None
    if not errors:
        file_inventory = sorted(
            {
                *(_relative_path(path, paths.repo_root) for path in run_config_paths),
                *(_relative_path(path, paths.repo_root) for path in registry_paths),
                *(_relative_path(path, paths.repo_root) for path in fixture_files),
                _relative_path(config_snapshot_path, paths.repo_root)
                if config_snapshot_path
                else "",
            }
        )
        file_inventory = [path for path in file_inventory if path]
        tooling_versions = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        }
        app_version = os.environ.get("APP_VERSION")
        if app_version:
            tooling_versions["app_version"] = app_version

        manifest = {
            "release_id": args.release,
            "created_at_utc": created_at,
            "git_commit": _git_commit_hash(paths.repo_root),
            "hashes": {
                "config_snapshot_hash": config_snapshot_hash,
                "registry_bundle_hash": registry_bundle_hash,
                "run_config_hashes": dict(sorted(run_config_hashes.items())),
            },
            "file_inventory": file_inventory,
            "tooling_versions": tooling_versions,
        }

        manifest_path = output_release_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    attestation = _format_attestation(
        args.release,
        created_at,
        errors,
        run_config_hashes,
        config_snapshot_hash,
        registry_bundle_hash,
    )
    attestation_path = output_release_dir / "phase0_attestation.md"
    attestation_path.write_text(attestation, encoding="utf-8")

    return Phase0Result(manifest_path=manifest_path, attestation_path=attestation_path, errors=errors)


def main() -> None:
    result = run_phase0_readiness(sys.argv[1:])
    if result.errors:
        for error in result.errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)
    print(f"Phase 0 readiness passed. Manifest: {result.manifest_path}")


if __name__ == "__main__":
    main()
