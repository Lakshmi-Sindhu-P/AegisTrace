"""Cross-check the tracked experiment registry against current evidence artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aegistrace.schemas.experiments import SEALED_SCENARIO_ID, ExperimentRegistry


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry", type=Path, default=Path("docs/experiment_registry.json")
    )
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"evidence artifact must be an object: {path}")
    return payload


def _check_artifacts(registry: ExperimentRegistry) -> tuple[int, int]:
    checked = 0
    missing = 0
    for run in registry.runs:
        if SEALED_SCENARIO_ID in (*run.training_scenarios, *run.validation_scenarios):
            raise ValueError(f"sealed Scenario 7 appears in run metadata: {run.experiment_id}")
        for reference in run.artifact_refs:
            path = Path(reference.path)
            if not path.exists():
                missing += 1
                continue
            checked += 1
            if _sha256(path) != reference.digest:
                raise ValueError(f"artifact digest mismatch: {reference.path}")
        for documentation in run.documentation_refs:
            if not Path(documentation).exists():
                raise ValueError(f"missing documentation reference: {documentation}")
    return checked, missing


def _check_known_artifacts(registry: ExperimentRegistry) -> int:
    checked = 0
    for run in registry.runs:
        for reference in run.artifact_refs:
            path = Path(reference.path)
            if not path.exists() or not path.name.endswith(".json"):
                continue
            artifact = _load_json(path)
            validation = artifact.get("validation_scenarios", [])
            if SEALED_SCENARIO_ID in validation:
                raise ValueError(f"sealed Scenario 7 appears in artifact: {path}")
            scenario_7 = artifact.get("scenario_7")
            if isinstance(scenario_7, dict) and scenario_7.get("loaded"):
                raise ValueError(f"artifact indicates Scenario 7 was loaded: {path}")
            if run.experiment_id == "phase3-causal-overlap-1.1.0-vs-1.2.0":
                counts = artifact["case_category_counts"]
                if sum(counts.values()) != artifact["malicious_case_count"]:
                    raise ValueError("overlap category counts do not reconcile")
            if (
                run.experiment_id == "phase3-aggregate-uncertainty-1.0.0"
                and artifact.get("scenario_7", {}).get("loaded")
            ):
                raise ValueError("uncertainty artifact indicates Scenario 7 was loaded")
            checked += 1
    return checked


def main() -> int:
    args = _parser().parse_args()
    try:
        registry = ExperimentRegistry.model_validate(
            json.loads(args.registry.read_text(encoding="utf-8"))
        )
        checked, missing = _check_artifacts(registry)
        known = _check_known_artifacts(registry)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError, ValueError) as error:
        print(error)
        return 1
    print(
        json.dumps(
            {
                "registry": args.registry.as_posix(),
                "runs": len(registry.runs),
                "checked_artifacts": checked,
                "checked_known_artifacts": known,
                "missing_generated_artifacts": missing,
                "scenario_7": "sealed",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
