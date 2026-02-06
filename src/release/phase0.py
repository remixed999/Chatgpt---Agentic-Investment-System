from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.core.config.loader import load_json_file
from src.core.utils.determinism import stable_json_dumps
from src.release.manifest import compute_manifest, verify_manifest
from src.release.parity import run_parity_checks
from src.schemas.models import ConfigSnapshot, PortfolioConfig, PortfolioSnapshot, RunConfig


@dataclass
class Phase0Result:
    ok: bool
    report: Dict[str, Any]
    violations: List[str]


def _load_manifest(bundle_dir: Path) -> Tuple[Dict[str, Any] | None, List[str]]:
    manifest_path = bundle_dir / "release_manifest.json"
    if not manifest_path.exists():
        return None, ["release_manifest.json is missing from bundle."]
    try:
        manifest = load_json_file(manifest_path).data
    except Exception as exc:
        return None, [f"Failed to read release_manifest.json: {exc}"]
    if not isinstance(manifest, dict):
        return None, ["release_manifest.json must contain an object."]
    return manifest, []


def _validate_schema(bundle_dir: Path) -> List[str]:
    violations: List[str] = []
    files = {
        "portfolio_snapshot.json": PortfolioSnapshot,
        "portfolio_config.json": PortfolioConfig,
        "run_config.json": RunConfig,
        "config_snapshot.json": ConfigSnapshot,
    }
    for filename, model in files.items():
        path = bundle_dir / filename
        if not path.exists():
            violations.append(f"Missing required bundle file: {filename}.")
            continue
        try:
            payload = load_json_file(path).data
            model.model_validate(payload)
        except Exception as exc:
            violations.append(f"Schema validation failed for {filename}: {exc}")
    return violations


def _bundle_identifiers(bundle_dir: Path) -> Dict[str, Any]:
    snapshot = PortfolioSnapshot.model_validate(load_json_file(bundle_dir / "portfolio_snapshot.json").data)
    run_config = RunConfig.model_validate(load_json_file(bundle_dir / "run_config.json").data)
    config_snapshot = ConfigSnapshot.model_validate(load_json_file(bundle_dir / "config_snapshot.json").data)
    return {
        "portfolio_id": snapshot.portfolio_id,
        "as_of_date": snapshot.as_of_date,
        "run_mode": run_config.run_mode,
        "rubric_version": config_snapshot.rubric_version,
    }


def run_phase0(bundle_dir: Path) -> Phase0Result:
    violations: List[str] = []
    manifest, manifest_errors = _load_manifest(bundle_dir)
    violations.extend(manifest_errors)
    if manifest is None:
        report = {
            "status": "FAIL",
            "violations": violations,
        }
        return Phase0Result(ok=False, report=report, violations=violations)

    manifest_ok, manifest_violations = verify_manifest(bundle_dir, manifest)
    violations.extend(manifest_violations)

    schema_violations = _validate_schema(bundle_dir)
    violations.extend(schema_violations)

    parity_violations = run_parity_checks()
    violations.extend(parity_violations)

    computed_manifest = compute_manifest(bundle_dir)
    computed_manifest["release_id"] = manifest.get("release_id")
    computed_manifest["created_at_utc"] = manifest.get("created_at_utc")
    report = {
        "status": "PASS" if not violations else "FAIL",
        "release_id": manifest.get("release_id"),
        "created_at_utc": manifest.get("created_at_utc"),
        "bundle_dir": str(bundle_dir),
        "manifest": {
            "expected": manifest,
            "computed": computed_manifest,
            "ok": manifest_ok,
            "violations": manifest_violations,
        },
        "schema_validation": {
            "ok": not schema_violations,
            "violations": schema_violations,
        },
        "parity": {
            "ok": not parity_violations,
            "violations": parity_violations,
        },
        "bundle_identifiers": _bundle_identifiers(bundle_dir) if not schema_violations else {},
        "violations": violations,
    }
    return Phase0Result(ok=not violations, report=report, violations=violations)


def write_report(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json_dumps(report) + "\n", encoding="utf-8")
